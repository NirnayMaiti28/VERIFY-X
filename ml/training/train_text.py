import os
import json
import yaml
import argparse
import inspect
import sys
import warnings

import torch
import datasets
import transformers
import peft
import trl

from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed
)
from peft import (
    LoraConfig,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer, SFTConfig

warnings.filterwarnings("ignore")

def parse_args():
    parser = argparse.ArgumentParser(description="VERIFY-X 2.0 Text Model QLoRA Training")
    parser.add_argument(
        "--config", 
        type=str, 
        default="../configs/text_qlora.yaml",
        help="Path to the training configuration YAML file"
    )
    parser.add_argument(
        "--test-only", 
        action="store_true",
        help="Run only the dataset loading and formatting stage to verify data, then exit."
    )
    return parser.parse_args()

def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_kwargs_from_signature(target_func, desired_kwargs):
    """
    Returns a dictionary of only the kwargs that are accepted by target_func.
    Warns about dropped arguments.
    """
    try:
        sig = inspect.signature(target_func)
        supported_params = set(sig.parameters.keys())
    except ValueError:
        return desired_kwargs

    actual_kwargs = {}
    dropped = []
    
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    is_dataclass = hasattr(target_func, '__dataclass_fields__') or (
        isinstance(target_func, type) and hasattr(target_func, '__dataclass_fields__')
    )
    
    for k, v in desired_kwargs.items():
        if k in supported_params:
            actual_kwargs[k] = v
        elif has_varkw and not is_dataclass:
            actual_kwargs[k] = v
        else:
            dropped.append(k)
            
    if dropped:
        func_name = getattr(target_func, '__name__', str(target_func))
        print(f"    [Warning] The following arguments were dropped because {func_name} does not support them: {dropped}")
        
    return actual_kwargs

def chunk_evidence(evidence_text, max_chars=1200):
    """Truncates evidence intelligently to prevent OOM on 6GB GPUs."""
    if len(evidence_text) <= max_chars:
        return evidence_text
    
    # Simple chunking: take the first max_chars
    # In a real pipeline, you'd pick sentences, but string slicing ensures strict memory limits.
    chunked = evidence_text[:max_chars]
    last_period = chunked.rfind('.')
    if last_period > max_chars // 2:
        return chunked[:last_period+1] + " [TRUNCATED]"
    return chunked + "... [TRUNCATED]"

def format_instruction(example):
    """
    Format a dataset example into the VERIFY-X standard instruction format.
    Uses 'prompt' and 'completion' to enforce strict structure.
    """
    system_prompt = "You are a fact verification model."
    claim = example.get("claim", "")
    
    evidence_text = ""
    evidence_list = example.get("evidence") or []
    
    if isinstance(evidence_list, list):
        for i, ev in enumerate(evidence_list):
            text = ev.get("text", "") if isinstance(ev, dict) else str(ev)
            evidence_text += f"[E{i+1}]\n{text}\n\n"
    elif isinstance(evidence_list, str):
        evidence_text += f"[E1]\n{evidence_list}\n\n"
    
    if not evidence_text.strip():
        evidence_text = "[E1]\nNo reliable evidence provided.\n"
        
    # Truncate evidence heavily to fit 512 context length for 6GB VRAM
    evidence_text = chunk_evidence(evidence_text.strip())
        
    task_prompt = "Determine the veracity of the claim."
    
    prompt = (
        f"SYSTEM:\n{system_prompt}\n\n"
        f"CLAIM:\n{claim}\n\n"
        f"EVIDENCE:\n{evidence_text}\n\n"
        f"TASK:\n{task_prompt}\n"
        f"### RESPONSE:\n"
    )
    
    label = example.get("label", "NOT_ENOUGH_INFORMATION")
    evidence_ids = [f"E{i+1}" for i in range(len(evidence_list) if isinstance(evidence_list, list) else 1)]
    if not evidence_ids and evidence_text != "[E1]\nNo reliable evidence provided.\n":
        evidence_ids = ["E1"]
        
    # Dynamic reason based on evidence
    reason = "No evidence was found to support or refute the claim."
    if label == "TRUE":
        reason = "The provided evidence explicitly supports the claims made."
    elif label == "FALSE":
        reason = "The provided evidence directly contradicts the claims made."
    elif label == "MISLEADING":
        reason = "The evidence shows the claim lacks critical context or distorts facts."
    elif label == "PARTIALLY_TRUE":
        reason = "The evidence supports some parts of the claim but refutes others."
        
    response_obj = {
        "verdict": label,
        "reason": reason,
        "evidence_ids": evidence_ids
    }
    
    response_json = json.dumps(response_obj, indent=2)
    
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
    
    summary = {
        "FEVER": 0,
        "LIAR": 0,
        "total": 0,
        "skipped": 0,
        "label_distribution": {}
    }
    
    label_map = config["dataset"].get("label_map", {})
    
    for source in config["dataset"]["sources"]:
        name = source["name"]
        path = source["path"]
        split = source.get("split", "train")
        
        print(f"    - Loading {name} from {path} ({split})")
        
        load_kwargs = {}
        if path == "fever/fever":
            load_kwargs["revision"] = "refs/convert/parquet"
        elif path == "liar":
            path = "rickpereira/liar"
            
        try:
            raw_ds = load_dataset(path, split=split, trust_remote_code=False, **load_kwargs)
        except Exception as e:
            print(f"    ! Failed to load {name}: {e}. Skipping.")
            continue
            
        if "label" in raw_ds.features and hasattr(raw_ds.features["label"], "int2str"):
            def int_to_str(ex):
                if ex["label"] != -1 and ex["label"] is not None:
                    ex["label_str"] = raw_ds.features["label"].int2str(ex["label"])
                else:
                    ex["label_str"] = "UNKNOWN"
                return ex
            raw_ds = raw_ds.map(int_to_str, desc=f"Converting labels for {name}")
            label_col = "label_str"
        else:
            label_col = "label"
            
        def normalize_example(example):
            claim = example.get("claim") or example.get("statement") or example.get("text")
            label_val = example.get(label_col)
            
            str_label = str(label_val)
            mapped_label = label_map.get(str_label, str_label)
            
            evidence = example.get("evidence") or []
            return {"claim": claim, "label": mapped_label, "evidence": evidence}

        norm_ds = raw_ds.map(normalize_example, desc=f"Normalizing schema for {name}")
        
        def is_valid(example):
            return bool(example.get("claim") and example.get("label") and example.get("label") != "UNKNOWN")

        initial_len = len(norm_ds)
        valid_ds = norm_ds.filter(is_valid, desc=f"Filtering {name}")
        skipped = initial_len - len(valid_ds)
        summary["skipped"] += skipped
        
        valid_ds = valid_ds.select_columns(["claim", "label", "evidence"])
        
        count = len(valid_ds)
        if name.lower() == "fever":
            summary["FEVER"] += count
        elif name.lower() == "liar":
            summary["LIAR"] += count
        summary["total"] += count
        
        datasets_to_merge.append(valid_ds)
    
    if not datasets_to_merge:
        raise ValueError("No datasets could be loaded.")
        
    merged_ds = datasets.concatenate_datasets(datasets_to_merge)
    merged_ds = merged_ds.shuffle(seed=config["dataset"]["seed"])
    
    for ex in merged_ds:
        lbl = ex["label"]
        summary["label_distribution"][lbl] = summary["label_distribution"].get(lbl, 0) + 1
        
    print("\n" + "="*40)
    print("VERIFY-X DATASET SUMMARY")
    print("="*40)
    print(f"FEVER examples loaded: {summary['FEVER']}")
    print(f"LIAR examples loaded:  {summary['LIAR']}")
    print(f"Total valid examples:  {summary['total']}")
    print(f"Malformed skipped:     {summary['skipped']}")
    print("Label Distribution:")
    for lbl, count in summary["label_distribution"].items():
        print(f"  - {lbl}: {count}")
    print("="*40 + "\n")
    
    print("[*] Formatting dataset into instructions...")
    formatted_ds = merged_ds.map(format_instruction, remove_columns=merged_ds.column_names, desc="Formatting prompts")
    
    print("[*] Splitting dataset...")
    val_split = config["dataset"].get("validation_split", 0.1)
    split_ds = formatted_ds.train_test_split(test_size=val_split, seed=config["dataset"]["seed"])
    
    print(f"Final Train Size: {len(split_ds['train'])}")
    print(f"Final Val Size:   {len(split_ds['test'])}")
    
    return split_ds

def run_hardware_checks(config):
    """Perform pre-flight GPU and memory diagnostic checks."""
    print("="*40)
    print("HARDWARE DIAGNOSTICS")
    print("="*40)
    
    if not torch.cuda.is_available():
        print("[WARNING] No CUDA GPU available! PyTorch is not recognizing your GPU.")
        print("[WARNING] The script will fall back to CPU execution.")
        print("[WARNING] 4-bit quantization will be automatically disabled, which requires ~16GB RAM.")
        config["quantization"]["bits"] = 16  # Disable 4-bit for CPU
        config["training"]["bf16"] = False
        config["training"]["fp16"] = False
        config["training"]["use_cpu"] = True
        return config
        
    device = torch.device("cuda:0")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"Total VRAM: {total_mem:.2f} GB")
    
    if total_mem < 5.5:
        print("[WARNING] GPU has less than 6GB VRAM. You may experience OOM errors.")
        print("[WARNING] If OOM occurs, reduce max_seq_length to 384 or 256 in text_qlora.yaml.")
        
    bf16_supported = torch.cuda.is_bf16_supported()
    print(f"BF16 Supported: {bf16_supported}")
    
    if config["training"].get("bf16", False) and not bf16_supported:
        print("[WARNING] BF16 is enabled in config, but GPU does not support it.")
        print("[WARNING] Automatically falling back to FP16.")
        config["training"]["bf16"] = False
        config["training"]["fp16"] = True
        
    print("="*40 + "\n")
    return config

def main():
    args = parse_args()
    config = load_config(args.config)
    set_seed(config["dataset"].get("seed", 42))
    
    print("="*40)
    print("ENVIRONMENT VERSIONS")
    print("="*40)
    print(f"TRL:          {trl.__version__}")
    print(f"Transformers: {transformers.__version__}")
    print(f"PEFT:         {peft.__version__}")
    print(f"Datasets:     {datasets.__version__}")
    print(f"PyTorch:      {torch.__version__}")
    print("="*40 + "\n")
    
    # 1. Dataset
    dataset = prepare_dataset(config)
    
    if args.test_only:
        print("\n[*] Dataset loading test complete. Exiting due to --test-only flag.")
        print("[*] Sample Train Prompt:")
        print(dataset["train"][0]["prompt"])
        print("[*] Sample Train Completion:")
        print(dataset["train"][0]["completion"])
        sys.exit(0)
        
    # 2. Hardware Checks
    config = run_hardware_checks(config)
    
    # 3. Tokenizer
    model_name = config["model"]["name"]
    print(f"[*] Loading tokenizer for {model_name}...")
    
    tokenizer_kwargs = {
        "pretrained_model_name_or_path": model_name,
        "trust_remote_code": config["model"].get("trust_remote_code", True)
    }
    tokenizer_kwargs = build_kwargs_from_signature(AutoTokenizer.from_pretrained, tokenizer_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(**tokenizer_kwargs)
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # 4. Quantization Config
    quant_cfg = config["quantization"]
    
    if torch.cuda.is_available():
        compute_dtype = torch.bfloat16 if config["training"].get("bf16") else torch.float16
        bnb_kwargs = {
            "load_in_4bit": quant_cfg["bits"] == 4,
            "bnb_4bit_quant_type": quant_cfg["quant_type"],
            "bnb_4bit_use_double_quant": quant_cfg["double_quant"],
            "bnb_4bit_compute_dtype": compute_dtype,
        }
        bnb_kwargs = build_kwargs_from_signature(BitsAndBytesConfig.__init__, bnb_kwargs)
        bnb_config = BitsAndBytesConfig(**bnb_kwargs)
    else:
        bnb_config = None
    
    # 5. Model Loading
    print(f"[*] Loading model {model_name}...")
    model_kwargs = {
        "pretrained_model_name_or_path": model_name,
        "device_map": "auto" if torch.cuda.is_available() else "cpu",
        "trust_remote_code": config["model"].get("trust_remote_code", True),
    }
    if bnb_config:
        model_kwargs["quantization_config"] = bnb_config
        
    model_kwargs = build_kwargs_from_signature(AutoModelForCausalLM.from_pretrained, model_kwargs)
    model = AutoModelForCausalLM.from_pretrained(**model_kwargs)
    
    model.config.use_cache = False
    
    prep_kbit_kwargs = {
        "model": model,
        "use_gradient_checkpointing": config["training"].get("gradient_checkpointing", True)
    }
    prep_kbit_kwargs = build_kwargs_from_signature(prepare_model_for_kbit_training, prep_kbit_kwargs)
    model = prepare_model_for_kbit_training(**prep_kbit_kwargs)
    
    # 6. LoRA Setup
    lora_cfg = config["lora"]
    lora_kwargs = {
        "r": lora_cfg["rank"],
        "lora_alpha": lora_cfg["alpha"],
        "lora_dropout": lora_cfg["dropout"],
        "target_modules": lora_cfg["target_modules"].split(",") if isinstance(lora_cfg["target_modules"], str) and lora_cfg["target_modules"] != "all-linear" else "all-linear",
        "bias": lora_cfg["bias"],
        "task_type": lora_cfg["task_type"],
    }
    lora_kwargs = build_kwargs_from_signature(LoraConfig.__init__, lora_kwargs)
    peft_config = LoraConfig(**lora_kwargs)
    
    # 7. Training Arguments (SFTConfig)
    train_cfg = config["training"]
    out_dir = config["output"]["dir"]
    os.makedirs(out_dir, exist_ok=True)
    
    total_steps = int((len(dataset["train"]) / (train_cfg["batch_size"] * train_cfg["gradient_accumulation_steps"])) * train_cfg["epochs"])
    warmup_steps = int(total_steps * train_cfg.get("warmup_ratio", 0.05))
    
    desired_sft_kwargs = {
        "output_dir": out_dir,
        "per_device_train_batch_size": train_cfg["batch_size"],
        "per_device_eval_batch_size": train_cfg["batch_size"],
        "gradient_accumulation_steps": train_cfg["gradient_accumulation_steps"],
        "learning_rate": train_cfg["learning_rate"],
        "lr_scheduler_type": train_cfg["lr_scheduler_type"],
        
        "warmup_ratio": train_cfg.get("warmup_ratio", 0.05),
        "warmup_steps": warmup_steps,
        
        "weight_decay": train_cfg["weight_decay"],
        "max_grad_norm": train_cfg["max_grad_norm"],
        "num_train_epochs": train_cfg["epochs"],
        "fp16": train_cfg.get("fp16", False),
        "bf16": train_cfg.get("bf16", False),
        "use_cpu": train_cfg.get("use_cpu", False),
        "logging_steps": train_cfg["logging_steps"],
        
        "save_strategy": "steps",
        "save_steps": train_cfg["save_steps"],
        "save_total_limit": train_cfg["save_total_limit"],
        "optim": train_cfg["optim"],
        
        "max_seq_length": train_cfg["max_seq_length"],
        "max_length": train_cfg["max_seq_length"],
        
        "report_to": ["mlflow"] if "mlflow" in config else ["tensorboard"],
        "run_name": config.get("mlflow", {}).get("experiment_name", "verifyx-training"),
    }
    
    if train_cfg.get("eval_steps"):
        desired_sft_kwargs["evaluation_strategy"] = "steps"
        desired_sft_kwargs["eval_strategy"] = "steps"
        desired_sft_kwargs["eval_steps"] = train_cfg["eval_steps"]
        
    try:
        sft_sig = inspect.signature(SFTConfig.__init__)
        supported_sft_params = set(sft_sig.parameters.keys())
        base_sig = inspect.signature(transformers.TrainingArguments.__init__)
        supported_sft_params.update(base_sig.parameters.keys())
    except ValueError:
        supported_sft_params = set(desired_sft_kwargs.keys())
        
    final_sft_kwargs = {}
    dropped_sft = []
    
    for k, v in desired_sft_kwargs.items():
        if k in supported_sft_params:
            final_sft_kwargs[k] = v
        else:
            dropped_sft.append(k)
            
    if "eval_strategy" in final_sft_kwargs and "evaluation_strategy" in final_sft_kwargs:
        del final_sft_kwargs["evaluation_strategy"]
        
    if "max_seq_length" in final_sft_kwargs and "max_length" in final_sft_kwargs:
        del final_sft_kwargs["max_length"]
        
    if "warmup_ratio" in final_sft_kwargs and "warmup_steps" in final_sft_kwargs:
        del final_sft_kwargs["warmup_steps"]
        
    if dropped_sft:
        print(f"    [Warning] Dropping unsupported SFTConfig arguments: {dropped_sft}")

    print("\n" + "="*40)
    print("FINAL TRAINING CONFIGURATION (SFTConfig)")
    print("="*40)
    for k, v in final_sft_kwargs.items():
        print(f"  {k}: {v}")
    print("="*40 + "\n")
    
    sft_config = SFTConfig(**final_sft_kwargs)
    
    # 8. Trainer Setup
    print("[*] Initializing SFTTrainer...")
    desired_trainer_kwargs = {
        "model": model,
        "train_dataset": dataset["train"],
        "eval_dataset": dataset["test"],
        "peft_config": peft_config,
        "args": sft_config,
        
        "processing_class": tokenizer,
        "tokenizer": tokenizer,
    }
    
    try:
        trainer_sig = inspect.signature(SFTTrainer.__init__)
        supported_trainer_params = set(trainer_sig.parameters.keys())
    except ValueError:
        supported_trainer_params = set(desired_trainer_kwargs.keys())
        
    final_trainer_kwargs = {}
    dropped_trainer = []
    
    for k, v in desired_trainer_kwargs.items():
        if k in supported_trainer_params:
            final_trainer_kwargs[k] = v
        else:
            dropped_trainer.append(k)
            
    if "processing_class" in final_trainer_kwargs and "tokenizer" in final_trainer_kwargs:
        del final_trainer_kwargs["tokenizer"]
        
    if dropped_trainer:
        print(f"    [Warning] Dropping unsupported SFTTrainer arguments: {dropped_trainer}")
        
    assert not isinstance(model, peft.PeftModel), "CRITICAL: Model is already a PeftModel before SFTTrainer."
        
    trainer = SFTTrainer(**final_trainer_kwargs)
    
    # 9. Dry-run validation success
    print("\n" + "="*50)
    print("VERIFY-X Qwen3-4B QLoRA training pipeline initialized successfully.")
    print("="*50 + "\n")
    
    print(f"Memory Allocated: {torch.cuda.memory_allocated() / (1024**3):.2f} GB")
    print(f"Memory Reserved: {torch.cuda.memory_reserved() / (1024**3):.2f} GB")
    
    # 10. Training
    print("[*] Starting training...")
    trainer.train()
    
    # 11. Save
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
