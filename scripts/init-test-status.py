#!/usr/bin/env python3
"""Инициализация test-status.json для ПМИ дашборда."""

import json, os
from datetime import datetime

CATEGORIES = {
    "K1": "Сетевые",
    "K2": "Вычислительные",
    "K3": "Память",
    "K4": "Дисковые",
    "K5": "Сервисные",
    "K6": "Каскадные",
    "K7": "Безопасность",
    "K8": "Платформенные",
    "K9": "Комплексные",
}

ML_METHODS = [
    {"id": "M1", "name": "Базовые метрики", "covered": False},
    {"id": "M2", "name": "Headroom", "covered": False},
    {"id": "M3", "name": "Пирсон (r)", "covered": False},
    {"id": "M4", "name": "Спирмен (ρ)", "covered": False},
    {"id": "M5", "name": "PCA", "covered": False},
    {"id": "M6", "name": "ARIMA", "covered": False},
    {"id": "M7", "name": "EVT", "covered": False},
]

def build():
    categories = []
    for kid, kname in CATEGORIES.items():
        # Парсим имена скриптов: rb-aither-k1-01-... → K1
        base = "/opt/aiops-aither/runbooks/aither"
        count = 0
        if os.path.isdir(base):
            count = len([f for f in os.listdir(base) if f.startswith(f"rb-aither-{kid.lower()}") and f.endswith('.sh')])
        categories.append({
            "id": kid, "name": f"{kid} — {kname}",
            "total": max(count, 1), "ok": 0, "fail": 0, "run": 0,
        })

    status = {
        "started_at": datetime.now().isoformat(),
        "categories": categories,
        "ml_methods": ML_METHODS,
        "current_test": None,
        "recent_events": [],
    }

    os.makedirs("/opt/aiops-aither/pmi", exist_ok=True)
    with open("/opt/aiops-aither/pmi/test-status.json", "w") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"✅ {sum(c['total'] for c in categories)} тестов в статус-файле")

if __name__ == '__main__':
    build()
