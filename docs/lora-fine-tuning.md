# LoRA Fine-tuning для Aither Platform

## Обзор

Дообучение моделей Qwen 2.5 на доменных знаниях РФ госсектора:
- Astra Linux SE 1.8.1 (Parsec, МКЦ, аудит)
- ГОСТы и требования ФСТЭК
- Kubernetes на Astra Linux
- YADRO VEGMAN S320, Proxmox, DRBD
- Aither Platform (биллинг, RAG, маршрутизация)

## Адаптеры

| Адаптер | Базовая модель | Ранг | Метод | Размер | Статус |
|---|---|---|---|---|---|
| `astra-14b` | Qwen2.5-14B-Instruct | r=8 | CPU LoRA | ~50 MB | 🔄 обучение |
| `astra-32b` | Qwen2.5-32B-Instruct | r=8 | QLoRA 4-bit | ~80 MB | ⬜ запланирован |

## Использование через API

```bash
curl -X POST http://gateway:30900/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-14b",
    "lora_adapter": "astra-14b",
    "messages": [{"role": "user", "content": "Как настроить Parsec в Astra Linux?"}]
  }'
```

## Интеграция с vLLM

vLLM 0.24.0 поддерживает LoRA через флаги:
```
--enable-lora
--lora-modules astra-14b=/models/lora-qwen14b-astra/
--max-lora-rank 8
```

## Технические детали

- **Реализация**: чистый PyTorch без peft (из-за air-gapped окружения)
- **LoRA Linear**: ручная реализация с low-rank матрицами
- **Обучение**: CPU (GPU занят vLLM), 3 эпохи, lr=2e-4
- **Датасет**: 21 пример (instruction/input/output)
- **Интеграция**: автоопределение адаптеров в Gateway при наличии директории
