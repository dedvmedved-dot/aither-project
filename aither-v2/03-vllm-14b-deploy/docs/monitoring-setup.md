# Monitoring Setup — GPU DCGM Exporter Canary

**Date:** 2026-07-18

---

## 1. DCGM Exporter статус — ✅

```console
Pods (gpu-operator):
  nvidia-dcgm-exporter-lvx6h   1/1 Running (n8)
  nvidia-dcgm-exporter-n2sn6   1/1 Running (n7)

Service:
  nvidia-dcgm-exporter   ClusterIP 10.107.11.191 → 9400/TCP
```

## 2. Port-forward — ✅

`kubectl port-forward -n gpu-operator svc/nvidia-dcgm-exporter 9400:9400`

## 3. Canary-check скрипт

**Путь:** `/root/canary-check.sh`  
**Период:** каждые 5 мин через cron  
**Проверяет:** `/health` HTTP 200 + `/metrics` с DCGM GPU метриками  

## 4. Метрики

| Метрика | Описание |
|---|---|
| `DCGM_FI_DEV_SM_CLOCK` | Частота SM ядра (MHz) |
| `DCGM_FI_DEV_MEM_CLOCK` | Частота памяти (MHz) |
| `DCGM_FI_DEV_GPU_TEMP` | Температура GPU (°C) |
| `DCGM_FI_DEV_POWER_USAGE` | Энергопотребление (W) |
| `DCGM_FI_DEV_GPU_UTIL` | Утилизация GPU (%) |
| `DCGM_FI_DEV_FB_FREE/USED` | Свободная/использованная VRAM (MiB) |

## 5. Статус — ✅ Canary PASSED

```
2026-07-18 22:17:28 [OK] Health check passed (HTTP 200)
2026-07-18 22:17:28 [OK] Metrics check passed — 2 GPU metrics found
```
