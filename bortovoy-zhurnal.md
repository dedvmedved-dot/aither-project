# Бортовой журнал — Aither Project

## 2026-07-03 — Старт проекта

### Контекст
- Hermes Agent v0.16.0 (VPS1) + v0.18.0 (VPS2, резерв)
- Провайдер: DeepSeek (deepseek-v4-pro, api.deepseek.com)
- Тестовая зона Cisco: доступна через VPS2 (Docker openconnect, tun1)
- HuaweiHP зона: доступна через VPS1 (tun0)
- WireGuard-мост VPS1↔VPS2: 10.99.0.0/24

### BMC серверы
- **10.129.40.50** — OpenBMC, Redfish 1.9.0, UUID c1b0a74d-...
- **10.129.40.51** — OpenBMC, Redfish 1.9.0, UUID 289530cf-...
- Доступ: web UI (https), учётка techvit (ограниченные права)
- SSH: недоступен (Permission denied)
- Redfish API: только root endpoint (/redfish/v1), остальное — 401

### Задачи
- [ ] Получить admin-доступ к BMC
- [ ] Инвентаризация аппаратного обеспечения
- [ ] Настройка удалённого управления питанием
- [ ] Мониторинг температуры/вентиляторов
- [ ] Обновление прошивок

### Репозиторий
- https://github.com/dedvmedved-dot/aither-project (private)
- SSH Deploy Key: ~/.ssh/id_ed25519_aither

---
*Журнал ведётся ассистентом Hermes в хронологическом порядке*
