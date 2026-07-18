# Source моделей — фиксация

## 32B модель (qwen-32b-base)

**Каталог:** `/data/models/Qwen2.5-32B-GPTQ`

### config.json
- model_type: qwen2
- architectures: ['Qwen2ForCausalLM']
- vocab_size: 152064
- hidden_size: 5120
- num_hidden_layers: 64
- num_attention_heads: 40
- intermediate_size: 27648
- torch_dtype: float16
- max_position_embeddings: 32768
- tie_word_embeddings: False
- **quantize_config.json: НЕТ** — модель FP16, не GPTQ

### tokenizer_config.json
- tokenizer_class: Qwen2Tokenizer
- chat_template: ✅ Да (2507 символов)
- eos_token: `<|im_end|>` (id: 151645)
- pad_token: `<|endoftext|>` (id: 151643)
- vocab_size (tokenizer): 151665

### Файлы safetensors (5 shards)
| Файл | Размер |
|---|---|
| model-00001-of-00005.safetensors | 3,945,876,416 B |
| model-00002-of-00005.safetensors | 3,983,771,264 B |
| model-00003-of-00005.safetensors | 3,951,056,216 B |
| model-00004-of-00005.safetensors | 3,983,861,408 B |
| model-00005-of-00005.safetensors | 3,479,419,512 B |
| **Всего** | **~19.3 GB** |

**Идентичность на n7 и n8:** Размеры файлов совпадают.

**Замечание:** Точный HuggingFace источник и commit SHA не зафиксированы. Модель взята из репозитория Qwen2.5-32B (вероятно Base, не Instruct). Полные SHA256 safetensors не завершены (файлы ~4ГБ, таймаут exec в Pod).

---

## 14B модель (qwen-14b)

**Каталог:** `/data/models/Qwen2.5-14B-Instruct`

### config.json
- model_type: qwen2
- architectures: ['Qwen2ForCausalLM']
- vocab_size: 152064
- hidden_size: 5120
- num_hidden_layers: 48
- num_attention_heads: 40
- intermediate_size: 27648
- torch_dtype: bfloat16
- max_position_embeddings: 32768

### Файлы safetensors (8 shards)
| Файл | Размер |
|---|---|
| model-00001-of-00008.safetensors | 3,885,154,816 B |
| model-00002-of-00008.safetensors | 3,995,327,992 B |
| model-00003-of-00008.safetensors | 3,995,328,080 B |
| model-00004-of-00008.safetensors | 3,995,338,432 B |
| model-00005-of-00008.safetensors | 3,979,624,824 B |
| model-00006-of-00008.safetensors | 3,995,328,080 B |
| model-00007-of-00008.safetensors | 3,995,328,080 B |
| model-00008-of-00008.safetensors | 1,698,703,696 B |
| **Всего** | **~28 GB** |
