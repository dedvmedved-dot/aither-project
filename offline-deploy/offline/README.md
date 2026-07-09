# Офлайн-зависимости

Инструкция по переносу офлайн-пакета в закрытый контур.

## Состав

| Каталог | Содержание | Размер |
|---|---|---|
| `docker/` | Docker-образы (images.tar.gz) | ~10 GB |
| `pip/` | Python-пакеты (.whl) | ~50 MB |
| `npm/` | NPM-пакет портала (.tgz) | ~5 MB |
| `models/` | Инструкция по переносу моделей | 0 (модели ~50 GB отдельно) |

## Порядок переноса

### 1. На машине с интернетом (сборка)

```bash
cd offline-deploy/
make bundle    # docker save + pip download
```

### 2. Перенос на носитель

```bash
# Скопировать весь каталог offline-deploy/ на флешку/внешний диск
rsync -av --progress offline-deploy/ /media/USB/offline-deploy/
```

### 3. На целевой машине (загрузка)

```bash
cd /media/USB/offline-deploy/
make offline-load    # docker load + pip install
```

### 4. Модели — отдельно

Модели (~50 GB) не входят в пакет. Перенесите их через внешний диск:

```bash
# На машине с интернетом:
huggingface-cli download Qwen/Qwen2.5-14B-Instruct --local-dir /mnt/models/Qwen2.5-14B-Instruct
huggingface-cli download Qwen/Qwen2.5-32B-Instruct-GPTQ --local-dir /mnt/models/Qwen2.5-32B-Instruct-GPTQ

# Скопировать /mnt/models/ на внешний диск
# На целевой машине скопировать обратно в /mnt/models/
```

Подробнее: `models/transfer.sh`.
