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
    TrainingArguments,
    set_seed
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

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
    
    # In some datasets (like FEVER), evidence might be raw text instead of a list of dicts initially.
    # We will try to handle both for robustness.
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
    )
    
    # Mocking standard structured response during training
    label = example.get("label", "NOT_ENOUGH_INFORMATION")
    response_obj = {
        "verdict": label,
        "confidence": 0.90, # default high confidence for gold labels
        "reason": f"Based on the provided evidence, the claim is {label}.",
        "evidence_ids": [f"E{i+1}" for i in range(len(evidence_list) if isinstance(evidence_list, list) else 1)]
    }
    response_json = json.dumps(response_obj, indent=2)
    
    return {"text": f"{prompt}\n### RESPONSE:\n{response_json}\n<|endoftext|>"}

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
        
        # Load dataset
        # Note: In a real scenario, FEVER/LIAR require specific preprocessing to map to 'claim', 'evidence', 'label'
        # For this script, we'll assume the preprocessed versions are available or we map them here.
        try:
            raw_ds = load_dataset(path, split=split, trust_remote_code=True)
        except Exception as e:
            print(f"    ! Failed to load {name}: {e}. Skipping.")
            continue
        
        # Here we would map dataset-specific columns to 'claim', 'evidence', 'label'
        # If the dataset already has them, we proceed.
        # We will use a subset for demonstration purposes in Colab to keep it lightweight if testing
        raw_ds = raw_ds.shuffle(seed=config["dataset"]["seed"]).select(range(min(1000, len(raw_ds))))
        
        datasets_to_merge.append(raw_ds)
    
    if not datasets_to_merge:
        raise ValueError("No datasets could be loaded.")
    
    # Normally we'd concatenate them. Since columns differ, we'd map them first.
    # For simplicity, we assume they've been normalized via preprocessing scripts.
    merged_ds = datasets_to_merge[0] # taking the first for this implementation
    
    print("[*] Formatting dataset into instructions...")
    # Add dummy evidence if missing for testing
    def ensure_columns(example):
        if "claim" not in example:
            example["claim"] = example.get("statement", example.get("text", "Unknown claim"))
        if "label" not in example:
            example["label"] = "NOT_ENOUGH_INFORMATION"
        
        # Map labels based on config
        label_map = config["dataset"].get("label_map", {})
        str_label = str(example["label"])
        example["label"] = label_map.get(str_label, str_label)
        
        if "evidence" not in example:
            example["evidence"] = [{"text": "Synthetic evidence passage."}]
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
    
    # 6. Training Arguments
    train_cfg = config["training"]
    out_dir = config["output"]["dir"]
    os.makedirs(out_dir, exist_ok=True)
    
    training_args = TrainingArguments(
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
        evaluation_strategy="steps" if train_cfg.get("eval_steps") else "no",
        eval_steps=train_cfg.get("eval_steps"),
        save_strategy="steps",
        save_steps=train_cfg["save_steps"],
        save_total_limit=train_cfg["save_total_limit"],
        optim=train_cfg["optim"],
        report_to=["mlflow"] if "mlflow" in config else ["tensorboard"],
        run_name=config.get("mlflow", {}).get("experiment_name", "verifyx-training"),
    )
    
    # Using completion only collator so we only train on the response
    response_template = "### RESPONSE:\n"
    collator = DataCollatorForCompletionOnlyLM(response_template=response_template, tokenizer=tokenizer)
    
    # 7. Trainer Setup
    print("[*] Initializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=train_cfg["max_seq_length"],
        tokenizer=tokenizer,
        args=training_args,
        data_collator=collator,
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
