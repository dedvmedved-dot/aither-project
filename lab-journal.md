# Лабораторный журнал: Aither Single-Node MVP

**Проект:** Aither — Token-as-a-Service платформа  
**Репозиторий:** `dedvmedved-dot/aither-project`  
**Стенд:** YADRO VEGMAN S320, сервер 40.51 (bootsman-k8s-clnt01-n8-gpu)  
**Дата начала:** 04.07.2026

---

## Исходное состояние

- **40.51:** Astra Linux 1.8 (6.6.28-1), 2× Xeon 6258R (28C/56T ×2), 754 GB RAM, 2× RTX 6000 (24 GB), 42 TB SAS SSD
- **40.50:** недоступен (RAID сбой + CMOS 2001г)
- **VPS2:** 130.17.1.90, SSH-туннели к BMC, доступ к 40.51 через sshpass
- **NVIDIA-драйвер:** не установлен
- **Docker:** не установлен
- **Kubernetes:** kubectl v1.33.5 (только клиент)

## Цель

Адаптировать ТР №1 (ядро Aither) и ТР №2 (портал) под single-node MVP на 40.51 + VPS2. Пройти Gate 0 → Gate 5.

---

### Шаг 0: Подготовка репозитория

**Цель:** привести репозиторий в состояние, соответствующее lab-workflow.

**Выполнено:**
- Удалены лишние репозитории (vegman-lab, yadro-gpu-lab)
- Всё перенесено в `aither-project`
- Обновлена спецификация 40.51 по реальному железу
- Создан документ адаптации `references/single-node-adaptation.md`
- Удалены устаревшие схемы (topology-2026-06-21.*)
- Добавлена актуальная топология (yadro-topology.*)

Статус: ✅ OK
