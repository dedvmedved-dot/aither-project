# Схема разметки дисков — Aither Platform

## Оборудование (один сервер)

### Контроллер MegaRAID

| Тип | Количество | Объём | Суммарно |
|---|---|---|---|
| SSD | 2 | 1.746 TB | ~3.5 TB |
| SSD | 10 | 3.492 TB | ~34.9 TB |
| **Итого MegaRAID** | **12** | | **~38.4 TB** |

### M.2

| Тип | Количество | Объём | Суммарно |
|---|---|---|---|
| NVMe SSD | 2 | 480 GB | **~960 GB** |

## План разметки (node01 / node02 — идентично)

```
/-------------------------------------------------------------------\
|                        MEGA RAID 12× SSD                          |
|                             ~38.4 TB                               |
|-------------------------------------------------------------------|
|  VD-1: OS (RAID1, 2×1.7TB)  |  VD-2: DATA (RAID10, 10×3.5TB)     |
|           ~1.7 TB usable     |           ~17.5 TB usable           |
|------------------------------|--------------------------------------|
|  /                200 GB     |  /data/models     5 TB  (vLLM)     |
|  /var/lib/docker  300 GB    |  /data/postgres   2 TB  (Portal DB)|
|  /var/log         200 GB     |  /data/backup     3 TB             |
|  swap             128 GB     |  /data/k3s        5 TB  (PVC)     |
|  резерв           ~900 GB    |  резерв           ~2.5 TB          |
|______________________________|______________________________________|

                        M.2 NVMe 2× 480GB
                        ┌──────────────────┐
                        │ /nvme/cache       │
                        │  ~960 GB RAID1   │
                        │  (Docker overlay, │
                        │   Redis, tmpfs)   │
                        └──────────────────┘
```

## План создания RAID-групп

### Шаг 1: Создать RAID1 из 2× 1.7 TB SSD (системный)

```
MegaRAID VD-1:
  RAID Level: 1
  Disks: 2× 1.746 TB SSD
  Name: OS
  Size: ~1.7 TB
  Stripe: 64 KB
  Policy: WriteBack, ReadAhead
```

### Шаг 2: Создать RAID10 из 10× 3.5 TB SSD (данные)

```
MegaRAID VD-2:
  RAID Level: 10
  Disks: 10× 3.492 TB SSD
  Name: DATA
  Size: ~17.5 TB
  Stripe: 256 KB
  Policy: WriteBack, ReadAhead, CachedIO
```

### Шаг 3: M.2 — оставить как есть (уже RAID1?)

```
M.2:
  Режим: аппаратный RAID1 (если поддерживается)
  ИЛИ: программный RAID1 (mdadm) при установке ОС
  Точка монтирования: /nvme/cache
  Назначение: Docker overlay2, Redis, временные файлы
```

## Файловые системы

| Точка монтирования | Файловая система | Размер | Назначение |
|---|---|---|---|
| / | XFS | 200 GB | RED OS |
| /var/lib/docker | XFS | 300 GB | Docker-образы, контейнеры |
| /var/log | XFS | 200 GB | Журналы |
| swap | swap | 128 GB | Подкачка (с RAM 768 GB — минимально) |
| /nvme/cache | XFS | ~960 GB | Быстрый кэш (M.2) |
| /data/models | XFS | 5 TB | Файлы моделей для vLLM |
| /data/postgres | XFS | 2 TB | Данные PostgreSQL |
| /data/backup | XFS | 3 TB | Резервные копии |
| /data/k3s | XFS | 5 TB | Persistent Volumes K3s |

## Примечания

- **RAID10** (а не RAID5/6) для данных — приоритет производительности для моделей
- **XFS** — рекомендован для production PostgreSQL и Docker
- **M.2 под Docker** — критически важно для производительности overlay2
- swap = 128 GB при 768 GB RAM — минимально, только для аварийного OOM
