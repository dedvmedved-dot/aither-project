#!/usr/bin/env python3
"""
LoRA fine-tuning для Qwen 2.5 14B на доменных знаниях РФ госсектора.
Запускается как Kubernetes Job на узле с GPU.
"""

import os
import sys
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, TaskType

# Конфигурация
MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct"
OUTPUT_DIR = "/mnt/models/lora-qwen14b-astra"
DATA_PATH = "/data/dataset.jsonl"

# Загрузка датасета
print("=== Загрузка датасета ===")
with open(DATA_PATH) as f:
    examples = [json.loads(line) for line in f if line.strip()]

print(f"Загружено примеров: {len(examples)}")

# Форматирование в instruction-формат
def format_instruction(example):
    return f"""<|im_start|>system
{example['instruction']}<|im_end|>
<|im_start|>user
{example['input']}<|im_end|>
<|im_start|>assistant
{example['output']}<|im_end|>"""

texts = [format_instruction(ex) for ex in examples]
dataset = Dataset.from_dict({"text": texts})

# Токенизатор
print("=== Загрузка токенизатора ===")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

def tokenize_function(examples):
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=2048,
        padding=False,
    )
    result["labels"] = result["input_ids"].copy()
    return result

tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
print(f"Токенизировано: {len(tokenized_dataset)} примеров")

# Модель
print("=== Загрузка модели ===")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)
model.enable_input_require_grads()
print(f"Модель загружена. Память GPU: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

# Конфигурация LoRA
print("=== Настройка LoRA ===")
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                      # ранг
    lora_alpha=32,             # alpha
    lora_dropout=0.05,
    target_modules=[           # модули Qwen2.5
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",
)

model = get_peft_model(model, lora_config)
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
total_params = sum(p.numel() for p in model.parameters())
print(f"Trainable: {trainable_params:,} / Total: {total_params:,} ({100*trainable_params/total_params:.2f}%)")

# Data collator
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    padding=True,
)

# Аргументы обучения
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

# Обучение
print("=== Начало обучения ===")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)

trainer.train()

# Сохранение адаптера
print("=== Сохранение адаптера ===")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

# Сохранение конфигурации для vLLM
lora_config_dict = {
    "lora_alpha": 32,
    "lora_rank": 16,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "base_model": MODEL_NAME,
    "dataset_size": len(examples),
    "epochs": 5,
}
with open(os.path.join(OUTPUT_DIR, "lora_config.json"), "w") as f:
    json.dump(lora_config_dict, f, indent=2)

print(f"=== ГОТОВО: адаптер сохранён в {OUTPUT_DIR} ===")
print(f"Размер адаптера: {sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)) / 1e6:.2f} MB")
