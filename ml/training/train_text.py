import os
import json
import yaml
import argparse
import torch
from datasets import load_dataset, DatasetDict
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer, SFTConfig

import warnings
warnings.filterwarnings("ignore")

def parse_args():
    parser = argparse.ArgumentParser(description="VERIFY-X 2.0 Text Model QLoRA Training")
    parser.add_argument(
        "--config", 
        type=str, 
        default="../configs/text_qlora.yaml",
        help="Path to the training configuration YAML file"
    )
    return parser.parse_args()

def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def format_instruction(example):
    """
    Format a dataset example into the VERIFY-X standard instruction format.
    Expects 'claim', 'evidence' (list of dicts), and 'label' in the dataset.
    """
    system_prompt = "You are a fact verification model."
    claim = example.get("claim", "")
    
    evidence_text = ""
    evidence_list = example.get("evidence", [])
    
    if isinstance(evidence_list, list):
        for i, ev in enumerate(evidence_list):
            if isinstance(ev, dict):
                text = ev.get("text", "")
            else:
                text = str(ev)
            evidence_text += f"[E{i+1}]\n{text}\n\n"
    elif isinstance(evidence_list, str):
        evidence_text += f"[E1]\n{evidence_list}\n\n"
    
    if not evidence_text.strip():
        evidence_text = "[E1]\nNo reliable evidence provided.\n"
        
    task_prompt = "Determine the veracity of the claim.\nReturn structured JSON."
    
    prompt = (
        f"SYSTEM:\n{system_prompt}\n\n"
        f"CLAIM:\n{claim}\n\n"
        f"EVIDENCE:\n{evidence_text.strip()}\n\n"
        f"TASK:\n{task_prompt}\n"
        f"### RESPONSE:\n"
    )
    
    label = example.get("label", "NOT_ENOUGH_INFORMATION")
    evidence_ids = [f"E{i+1}" for i in range(len(evidence_list) if isinstance(evidence_list, list) else 1)]
    if not evidence_ids and evidence_text != "[E1]\nNo reliable evidence provided.\n":
        evidence_ids = ["E1"]
        
    response_obj = {
        "verdict": label,
        "confidence": 0.90,
        "reason": f"Based on the provided evidence, the claim is {label}.",
        "evidence_ids": evidence_ids
    }
    
    response_json = json.dumps(response_obj, indent=2)
    
    # Provide 'prompt' and 'completion' for TRL's completion-only loss
    return {
        "prompt": prompt,
        "completion": response_json
    }

def prepare_dataset(config):
    """
    Loads and preprocesses datasets specified in the config.
    Returns a unified DatasetDict.
    """
    print("[*] Loading datasets...")
    datasets_to_merge = []
    
    for source in config["dataset"]["sources"]:
        name = source["name"]
        path = source["path"]
        split = source.get("split", "train")
        
        print(f"    - Loading {name} from {path} ({split})")
        
        try:
            raw_ds = load_dataset(path, split=split, trust_remote_code=True)
        except Exception as e:
            print(f"    ! Failed to load {name}: {e}. Skipping.")
            continue
        
        raw_ds = raw_ds.shuffle(seed=config["dataset"]["seed"]).select(range(min(1000, len(raw_ds))))
        datasets_to_merge.append(raw_ds)
    
    if not datasets_to_merge:
        raise ValueError("No datasets could be loaded.")
    
    merged_ds = datasets_to_merge[0]
    
    print("[*] Formatting dataset into instructions...")
    def ensure_columns(example):
        if "claim" not in example:
            example["claim"] = example.get("statement", example.get("text", "Unknown claim"))
        if "label" not in example:
            example["label"] = "NOT_ENOUGH_INFORMATION"
        
        label_map = config["dataset"].get("label_map", {})
        str_label = str(example["label"])
        example["label"] = label_map.get(str_label, str_label)
        
        if "evidence" not in example:
            example["evidence"] = []
        return example
        
    merged_ds = merged_ds.map(ensure_columns)
    formatted_ds = merged_ds.map(format_instruction, remove_columns=merged_ds.column_names)
    
    print("[*] Splitting dataset...")
    val_split = config["dataset"].get("validation_split", 0.1)
    split_ds = formatted_ds.train_test_split(test_size=val_split, seed=config["dataset"]["seed"])
    
    return split_ds

def main():
    args = parse_args()
    config = load_config(args.config)
    set_seed(config["dataset"].get("seed", 42))
    
    # 1. Dataset
    dataset = prepare_dataset(config)
    print(f"Train size: {len(dataset['train'])}, Val size: {len(dataset['test'])}")
    
    # 2. Tokenizer
    model_name = config["model"]["name"]
    print(f"[*] Loading tokenizer for {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=config["model"].get("trust_remote_code", True)
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # 3. Quantization Config
    quant_cfg = config["quantization"]
    compute_dtype = getattr(torch, quant_cfg["compute_dtype"])
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=quant_cfg["bits"] == 4,
        bnb_4bit_quant_type=quant_cfg["quant_type"],
        bnb_4bit_use_double_quant=quant_cfg["double_quant"],
        bnb_4bit_compute_dtype=compute_dtype,
    )
    
    # 4. Model Loading
    print(f"[*] Loading model {model_name} in 4-bit...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=config["model"].get("trust_remote_code", True),
    )
    
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(
        model, 
        use_gradient_checkpointing=config["training"].get("gradient_checkpointing", True)
    )
    
    # 5. LoRA Setup
    lora_cfg = config["lora"]
    peft_config = LoraConfig(
        r=lora_cfg["rank"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"].split(",") if isinstance(lora_cfg["target_modules"], str) and lora_cfg["target_modules"] != "all-linear" else "all-linear",
        bias=lora_cfg["bias"],
        task_type=lora_cfg["task_type"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # 6. Training Arguments (SFTConfig)
    train_cfg = config["training"]
    out_dir = config["output"]["dir"]
    os.makedirs(out_dir, exist_ok=True)
    
    sft_config = SFTConfig(
        output_dir=out_dir,
        per_device_train_batch_size=train_cfg["batch_size"],
        per_device_eval_batch_size=train_cfg["batch_size"],
        gradient_accumulation_steps=train_cfg["gradient_accumulation_steps"],
        learning_rate=train_cfg["learning_rate"],
        lr_scheduler_type=train_cfg["lr_scheduler_type"],
        warmup_ratio=train_cfg["warmup_ratio"],
        weight_decay=train_cfg["weight_decay"],
        max_grad_norm=train_cfg["max_grad_norm"],
        num_train_epochs=train_cfg["epochs"],
        fp16=train_cfg["fp16"],
        bf16=train_cfg["bf16"],
        logging_steps=train_cfg["logging_steps"],
        eval_strategy="steps" if train_cfg.get("eval_steps") else "no",
        eval_steps=train_cfg.get("eval_steps"),
        save_strategy="steps",
        save_steps=train_cfg["save_steps"],
        save_total_limit=train_cfg["save_total_limit"],
        optim=train_cfg["optim"],
        report_to=["mlflow"] if "mlflow" in config else ["tensorboard"],
        run_name=config.get("mlflow", {}).get("experiment_name", "verifyx-training"),
        max_seq_length=train_cfg["max_seq_length"],
        dataset_text_field=None,
    )
    
    # 7. Trainer Setup
    print("[*] Initializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        peft_config=peft_config,
        processing_class=tokenizer,
        args=sft_config,
    )
    
    # 8. Training
    print("[*] Starting training...")
    trainer.train()
    
    # 9. Save
    print(f"[*] Saving adapter to {out_dir}...")
    trainer.model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    
    if config["output"].get("push_to_hub"):
        hub_id = config["output"].get("hub_model_id")
        if hub_id:
            print(f"[*] Pushing adapter to Hub: {hub_id}")
            trainer.model.push_to_hub(hub_id)
            tokenizer.push_to_hub(hub_id)
            
    print("[*] Training complete!")

if __name__ == "__main__":
    main()
