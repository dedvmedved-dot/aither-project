# Aither Platform — решение проблем (v1.1, 10.07.2026)

## Чаты: ошибка 502 при отправке сообщений

**Симптом:** вкладка Network показывает 502 на `POST /api/v1/chats/:id/messages`.

**Причина:** Gateway не может обработать запрос — либо vLLM недоступен, либо Gateway заблокирован предыдущим стриминг-запросом (однопоточный режим).

**Решение:**
1. Проверить Gateway: `curl http://VPS1_IP:30900/health`
2. Проверить vLLM: `curl http://VPS1_IP:30900/v1/models`
3. Если Gateway однопоточный — добавить `ThreadingHTTPServer` в gateway.py
4. Перезапустить: `kubectl rollout restart deploy/gateway`

## Чаты: ошибка 403 «model_not_available» или «security_violation»

**Причина:** включены проверки тарифов/безопасности в Gateway (расширенная версия 43KB).

**Решение:** откатить Gateway к базовой версии (325 строк) без проверок:
```bash
kubectl create configmap gateway-code --from-file=gateway.py=gateway-simple.py --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deploy/gateway
```

## Пустой дашборд

**Симптом:** вкладка «Дашборд» показывает пустую страницу.

**Причина:** дубликат функции `renderDashboard` в index.html (вторая копия переопределяет оригинал).

**Решение:**
1. `grep -n "function renderDashboard" portal/static/index.html`
2. Удалить дубликат (второе вхождение)
3. Скопировать на VPS1: `scp static/index.html root@VPS1:/var/www/aither-portal/`
4. Перезагрузить nginx: `systemctl reload nginx`

## Кнопка «Перейти» на тарифах не работает

**Симптом:** `upgradeTier is not defined` в консоли браузера.

**Причина:** функция `highlightCode` не закрыта `}`, из-за чего `upgradeTier` оказывается в её локальной области видимости.

**Решение:** добавить закрывающую `}` после `highlightCode`.

## Статика устарела на VPS1

**Симптом:** изменения в index.html не отображаются на портале.

**Причина:** nginx на VPS1 раздаёт статику из `/var/www/aither-portal/` — это отдельная копия, не связанная с репозиторием на VPS2.

**Решение:**
```bash
scp root@VPS2:/root/aither-project/portal/static/index.html /tmp/
scp /tmp/index.html root@VPS1:/var/www/aither-portal/
ssh root@VPS1 'systemctl reload nginx'
```

## Gateway: ConfigMap потерял файлы при обновлении

**Симптом:** после `kubectl create configmap ... --from-file=gateway.py` под падает с `ModuleNotFoundError`.

**Причина:** `kubectl create --from-file` заменяет ВЕСЬ ConfigMap, удаляя другие файлы (admin.py, security.py и т.д.).

**Решение:** всегда указывать ВСЕ файлы при обновлении:
```bash
kubectl create configmap gateway-code   --from-file=gateway.py --from-file=admin.py --from-file=catalog.py   --from-file=catalog.yaml --from-file=hybrid_rag.py --from-file=metrics.py   --from-file=reaper.py --from-file=routing.py --from-file=security.py   --from-file=security_egress.py --from-file=vault.py --from-file=wiki_graph.py   --dry-run=client -o yaml | kubectl apply -f -
```

## PostgreSQL: ошибка «role does not exist»

**Симптом:** `psql -U aither` → `FATAL: role "aither" does not exist`.

**Причина:** в Docker-контейнере портала используется пользователь `portal`, а не `aither`.

**Решение:**
```bash
docker exec aither-portal-portal-db-1 psql -U portal -d portal
```
