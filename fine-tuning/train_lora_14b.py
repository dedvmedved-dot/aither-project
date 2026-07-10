#!/usr/bin/env python3
"""
QLoRA (4-bit) fine-tuning для Qwen 2.5 14B на доменных знаниях РФ госсектора.
Использует 4-bit квантование, чтобы влезть в 24 GB VRAM (RTX 6000).
"""
import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType

MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct"
OUTPUT_DIR = "/mnt/models/lora-qwen14b-astra"
DATA_PATH = "/data/dataset.jsonl"

print("=== Загрузка датасета ===")
with open(DATA_PATH) as f:
    examples = [json.loads(line) for line in f if line.strip()]
print(f"Загружено примеров: {len(examples)}")

def format_instruction(example):
    return f"""<|im_start|>system
{example['instruction']}<|im_end|>
<|im_start|>user
{example['input']}<|im_end|>
<|im_start|>assistant
{example['output']}<|im_end|>"""

texts = [format_instruction(ex) for ex in examples]
dataset = Dataset.from_dict({"text": texts})

print("=== Загрузка токенизатора ===")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

def tokenize_function(examples):
    result = tokenizer(examples["text"], truncation=True, max_length=2048, padding=False)
    result["labels"] = result["input_ids"].copy()
    return result

tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
print(f"Токенизировано: {len(tokenized_dataset)} примеров")

# 4-bit квантование — модель влезает в 24 GB VRAM
print("=== Загрузка модели (4-bit QLoRA) ===")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model = prepare_model_for_kbit_training(model)
model.enable_input_require_grads()
print(f"Модель загружена. Память GPU: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

print("=== Настройка QLoRA ===")
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
)

model = get_peft_model(model, lora_config)
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
total_params = sum(p.numel() for p in model.parameters())
print(f"Trainable: {trainable_params:,} / Total: {total_params:,} ({100*trainable_params/total_params:.2f}%)")

data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=5,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    warmup_steps=50,
    logging_steps=10,
    save_steps=50,
    save_total_limit=2,
    bf16=True,
    report_to="none",
    remove_unused_columns=False,
)

print("=== Начало обучения ===")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)
trainer.train()

print("=== Сохранение адаптера ===")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

lora_config_dict = {
    "lora_alpha": 32,
    "lora_rank": 16,
    "quantization": "4bit-nf4",
    "base_model": MODEL_NAME,
    "dataset_size": len(examples),
    "epochs": 5,
}
with open(os.path.join(OUTPUT_DIR, "lora_config.json"), "w") as f:
    json.dump(lora_config_dict, f, indent=2, ensure_ascii=False)

print(f"=== ГОТОВО: адаптер в {OUTPUT_DIR} ===")
