# Aither AI Platform — Руководство по резервному копированию и восстановлению

**Версия:** OPS-02-R2 | **Дата:** 26 июля 2026 | **Ревизия:** U1.3-OPS-R2

---

## 1. Что требуется резервировать

### 1.1. Инвентаризация компонентов

| Компонент | Тип | Приоритет | Метод |
|-----------|-----|-----------|-------|
| Portal DB (PostgreSQL, VPS2) | Данные | Критический | pg_dump |
| Aither DB (PostgreSQL, K8s) | Данные | Критический | pg_dump |
| ConfigMaps (5 шт.) | Конфигурация | Высокий | kubectl get -o yaml |
| Secrets (4 шт.) | Креды | Критический | kubectl get -o yaml (внешнее хранение) |
| Redis (rate-limit) | Кеш | Низкий | Не требует (пересоздаётся) |

### 1.2. Целевые показатели RPO/RTO (Operational target for Controlled Beta)

Примечание: приведённые значения являются операционными целевыми показателями для стадии Controlled Beta, а не жёсткими SLA. Фактические показатели могут варьироваться в зависимости от объёма данных и доступности инфраструктуры.

| Компонент | RPO | RTO | Метод восстановления | Способ проверки |
|-----------|-----|-----|---------------------|-----------------|
| Portal DB (PostgreSQL, VPS2) | 24 часа | 4 часа | pg_restore из последнего ежедневного дампа | Проверка количества таблиц и выборочных записей (см. раздел 7) |
| Aither DB (PostgreSQL, K8s) | 24 часа | 4 часа | pg_restore из последнего ежедневного дампа | Проверка схемы, количества таблиц, выборочных записей (см. раздел 7) |
| ConfigMaps (5 шт.) | 24 часа | 1 час | kubectl apply из резервных YAML-файлов | kubectl get configmap и сверка ключей |
| Secrets (4 шт.) | 24 часа | 2 часа | Расшифровка из зашифрованного бэкапа → kubectl apply (см. раздел 4 и 9) | Проверка наличия всех ключей в расшифрованном файле |
| Redis (rate-limit) | Не применимо | 10 минут | Автоматическое пересоздание при деплое | redis-cli PING, проверка счетчиков сброшены |
| PV/PVC (K8s Persistent Volumes) | Зависит от StorageClass | 4 часа | Восстановление из volume snapshot (при поддержке CSI) или ручное пересоздание PVC (см. раздел 8) | Проверка статуса PVC (Bound), проверка доступности данных в поде |

---

## 2. Резервное копирование

### PostgreSQL (VPS2 Portal DB)

```bash
ssh vps2 "pg_dump -U portal -h 127.0.0.1 portal > /backup/portal_db_$(date +%Y%m%d).sql"
```

### PostgreSQL (K8s Aither DB)

```bash
kubectl exec -n aither-inference deployment/postgres -- pg_dump -U aither aither > /backup/aither_db_$(date +%Y%m%d).sql
```

### ConfigMaps

```bash
for cm in aither-bff-config aither-portal-config aither-portal-frontend-config nginx-gateway-32b; do
    kubectl get configmap $cm -n aither-inference -o yaml > /backup/cm-${cm}-$(date +%Y%m%d).yaml
done
```

### Secrets

```bash
for secret in aither-bff-auth aither-identity-secret aither-ai-platform-secret vllm-api-key; do
    kubectl get secret $secret -n aither-inference -o yaml > /backup/secret-${secret}-$(date +%Y%m%d).yaml
done
```

**ВАЖНО:** После создания YAML-файлов Secrets они ДОЛЖНЫ быть немедленно зашифрованы, а незашифрованные оригиналы — удалены. См. раздел 4 «Шифрование» для детальных инструкций.

---

## 3. Расписание

| Частота | Что |
|---------|-----|
| Ежедневно | PostgreSQL дампы, ConfigMaps |
| При изменении | Secrets, ConfigMaps |
| Еженедельно | Полный снапшот |

---

## 4. Политика хранения (Retention Policy)

### 4.1. Уровни хранения

| Тип бэкапа | Периодичность | Срок хранения | Место хранения |
|-------------|---------------|---------------|----------------|
| Daily | Ежедневно | 7 дней | `/backup/daily/` |
| Weekly | Еженедельно (каждое воскресенье) | 4 недели | `/backup/weekly/` |
| Monthly | Ежемесячно (1-е число) | 3 месяца | `/backup/monthly/` |

### 4.2. Порядок удаления устаревших бэкапов

Удаление выполняется автоматически по cron. Принцип: при создании нового бэкапа проверяется количество существующих бэкапов данного уровня; все бэкапы старше указанного срока хранения удаляются.

```bash
# Пример: удаление daily-бэкапов старше 7 дней
find /backup/daily/ -type f -mtime +7 -delete

# Пример: удаление weekly-бэкапов старше 28 дней
find /backup/weekly/ -type f -mtime +28 -delete

# Пример: удаление monthly-бэкапов старше 90 дней
find /backup/monthly/ -type f -mtime +90 -delete
```

### 4.3. Защита от случайного удаления

- Все бэкапы на основном хосте имеют атрибут `chattr +i` (immutable) после создания. Перед удалением устаревших бэкапов атрибут снимается командой `chattr -i`.
- Резервная копия на off-site хранилище (см. раздел 6) НЕ подвержена автоматическому удалению по cron — удаление только ручное, с подтверждением.
- Критические бэкапы (monthly) дополнительно защищены отдельной учётной записью на off-site хранилище с доступом только на запись (append-only).

```bash
# Установка immutable-флага после создания бэкапа
chattr +i /backup/daily/portal_db_20260726.sql

# Снятие immutable-флага перед удалением
chattr -i /backup/daily/portal_db_20260719.sql
```

### 4.4. Known Limitation

На момент Controlled Beta политика хранения реализована через ручной или полуавтоматический cron на основном хосте. Автоматизированная система ротации с мониторингом и алертами запланирована на следующую итерацию.

---

## 5. Шифрование (Encryption)

### 5.1. Обязательное требование

**ЗАПРЕЩЕНО** хранение незашифрованных Secret YAML-файлов на диске. Все файлы, полученные командой `kubectl get secret -o yaml`, должны быть немедленно зашифрованы, а незашифрованные оригиналы — удалены (`shred -u`).

### 5.2. Доступные инструменты

- `gpg` (GNU Privacy Guard) — для асимметричного шифрования с ключами
- `openssl` — для симметричного шифрования с паролем

В данной процедуре используется **openssl с AES-256-CBC** как наиболее простой и надёжный метод, не требующий управления ключевой парой.

### 5.3. Параметры шифрования

- Алгоритм: AES-256-CBC
- Формат вывода: base64 (для безопасного хранения в текстовых файлах)
- Ключ: передаётся через файл или переменную окружения (НЕ в командной строке)

### 5.4. Шифрование файла

```bash
# Создание ключа шифрования (однократно, при настройке)
openssl rand -base64 32 > /backup/.backup_key
chmod 600 /backup/.backup_key

# Шифрование Secret YAML-файла
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in /backup/secret-aither-bff-auth-20260726.yaml \
    -out /backup/secret-aither-bff-auth-20260726.yaml.enc \
    -pass file:/backup/.backup_key

# Проверка, что зашифрованный файл создан и не является plaintext
file /backup/secret-aither-bff-auth-20260726.yaml.enc
# Ожидаемый вывод: "data" (бинарный зашифрованный контент)

# Удаление незашифрованного оригинала с перезаписью
shred -u /backup/secret-aither-bff-auth-20260726.yaml
```

### 5.5. Расшифровка файла

```bash
# Расшифровка в новый файл (НЕ перезапись зашифрованного)
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -in /backup/secret-aither-bff-auth-20260726.yaml.enc \
    -out /backup/secret-aither-bff-auth-20260726.yaml \
    -pass file:/backup/.backup_key

# После использования — немедленно удалить расшифрованный файл
kubectl apply -f /backup/secret-aither-bff-auth-20260726.yaml
shred -u /backup/secret-aither-bff-auth-20260726.yaml
```

### 5.6. Проверяемый пример (без реальных Secrets)

Для верификации процедуры используйте тестовый файл:

```bash
# Создание тестового файла
echo "Это тестовый Secret для проверки процедуры шифрования" > /tmp/test_secret.txt

# Шифрование
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in /tmp/test_secret.txt \
    -out /tmp/test_secret.txt.enc \
    -pass file:/backup/.backup_key

# Проверка: зашифрованный файл не содержит исходный текст
grep -q "тестовый Secret" /tmp/test_secret.txt.enc && echo "ОШИБКА: текст найден в зашифрованном файле" || echo "OK: зашифрованный файл не содержит plaintext"

# Расшифровка
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -in /tmp/test_secret.txt.enc \
    -out /tmp/test_secret_decrypted.txt \
    -pass file:/backup/.backup_key

# Проверка идентичности
diff /tmp/test_secret.txt /tmp/test_secret_decrypted.txt && echo "OK: расшифрованный файл идентичен оригиналу" || echo "ОШИБКА: файлы различаются"

# Очистка
shred -u /tmp/test_secret.txt /tmp/test_secret_decrypted.txt /tmp/test_secret.txt.enc
```

### 5.7. Управление ключом шифрования

- Ключ `/backup/.backup_key` должен иметь права `600` и владельца `root`
- Ключ НЕ должен храниться в том же репозитории, что и зашифрованные бэкапы
- Ключ должен быть скопирован в защищённое внешнее хранилище (см. раздел 6)
- Резервная копия ключа должна храниться отдельно от резервной копии данных (правило разделения учётных данных)

---

## 6. Проверка целостности (Integrity Verification)

### 6.1. Контрольные суммы

Для всех бэкапов при создании вычисляется и сохраняется контрольная сумма SHA-256. Перед восстановлением целостность проверяется повторно.

```bash
# Создание бэкапа с одновременным вычислением контрольной суммы
pg_dump -U aither aither > /backup/daily/aither_db_20260726.sql
sha256sum /backup/daily/aither_db_20260726.sql > /backup/daily/aither_db_20260726.sql.sha256

# Содержимое .sha256 файла (пример):
# a1b2c3d4e5f6...  /backup/daily/aither_db_20260726.sql
```

### 6.2. Проверка целостности перед восстановлением

```bash
# Проверка контрольной суммы
cd /backup/daily
sha256sum -c aither_db_20260726.sql.sha256
# Ожидаемый вывод: aither_db_20260726.sql: OK

# Если проверка не пройдена:
# aither_db_20260726.sql: FAILED
# sha256sum: WARNING: 1 computed checksum did NOT match
```

### 6.3. Проверка целостности зашифрованных файлов

```bash
# Контрольная сумма вычисляется от зашифрованного файла
sha256sum /backup/secret-aither-bff-auth-20260726.yaml.enc > /backup/secret-aither-bff-auth-20260726.yaml.enc.sha256

# Проверка
sha256sum -c /backup/secret-aither-bff-auth-20260726.yaml.enc.sha256
```

### 6.4. Регулярная верификация

Все контрольные суммы должны проверяться еженедельно (cron). Результаты логируются. При обнаружении несовпадения — немедленное оповещение и создание нового бэкапа.

```bash
# Скрипт еженедельной проверки
#!/bin/bash
FAILED=0
for sha in /backup/daily/*.sha256 /backup/weekly/*.sha256 /backup/monthly/*.sha256; do
    [ -f "$sha" ] || continue
    dir=$(dirname "$sha")
    cd "$dir" || continue
    if ! sha256sum -c "$(basename "$sha")" 2>/dev/null; then
        echo "[ALERT] Integrity check FAILED: $sha" | tee -a /var/log/backup-integrity.log
        FAILED=1
    fi
done
[ $FAILED -eq 0 ] && echo "[OK] All integrity checks passed: $(date)" >> /var/log/backup-integrity.log
```

---

## 7. Внешнее хранение (Off-site Copy)

### 7.1. Стратегия хранения

| Локация | Тип | Назначение |
|---------|-----|------------|
| **Primary:** `/backup/` на VPS2 (основной хост) | Локальный диск | Основное хранилище, оперативное восстановление |
| **Secondary:** Off-site хранилище (уточняется) | Внешнее/удалённое | Резервная копия на случай полной потери основного хоста |

### 7.2. Принцип 3-2-1 (честное MVP-ограничение)

Полноценное соблюдение правила 3-2-1 (три копии, два типа носителей, одна вне площадки) является целевым ориентиром. На стадии Controlled Beta действует **MVP-ограничение**:

- **Реализовано:** две копии данных (основной хост + одно внешнее хранилище)
- **Запланировано:** третий тип носителя (например, S3-совместимое холодное хранилище), автоматическая репликация

### 7.3. Разделение учётных данных

- Учётные данные для доступа к основному хосту и к off-site хранилищу **различны**
- Ключ шифрования бэкапов (`/backup/.backup_key`) хранится отдельно от самих бэкапов
- Доступ к off-site хранилищу имеет ограниченный круг лиц (не пересекающийся с доступом к основному хосту, где это возможно)

### 7.4. Процедура копирования на off-site

```bash
# Синхронизация зашифрованных бэкапов на внешнее хранилище
rsync -avz --delete \
    /backup/daily/ \
    /backup/weekly/ \
    /backup/monthly/ \
    user@offsite-storage.example.com:/backup/aither/

# Ключ шифрования копируется ОТДЕЛЬНО, по другому каналу
# (НЕ в той же rsync-команде, что и данные)
scp /backup/.backup_key user@secure-storage.example.com:/keys/aither/
```

---

## 8. Тестовое восстановление (Test Restore)

### 8.1. Процедура test restore

Тестовое восстановление выполняется во **временную среду**, изолированную от production. Цель — верифицировать целостность и пригодность бэкапа без воздействия на работающую систему.

#### Шаг 1: Создание временной среды

```bash
# Создание временного namespace в K8s
kubectl create namespace aither-restore-test

# Развёртывание временного PostgreSQL
kubectl apply -n aither-restore-test -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: postgres-test
spec:
  containers:
  - name: postgres
    image: postgres:16
    env:
    - name: POSTGRES_USER
      value: aither
    - name: POSTGRES_DB
      value: aither
    - name: POSTGRES_PASSWORD
      value: test_restore_temp
EOF
```

#### Шаг 2: Восстановление дампа

```bash
# Копирование дампа в под
kubectl cp /backup/daily/aither_db_20260726.sql \
    aither-restore-test/postgres-test:/tmp/dump.sql

# Восстановление
kubectl exec -n aither-restore-test postgres-test -- \
    psql -U aither aither < /tmp/dump.sql
```

#### Шаг 3: Проверка схемы

```bash
# Проверка количества таблиц в production
kubectl exec -n aither-inference deployment/postgres -- \
    psql -U aither -d aither -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# Проверка количества таблиц в test restore
kubectl exec -n aither-restore-test postgres-test -- \
    psql -U aither -d aither -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# Сравнение: количество таблиц должно совпадать
```

#### Шаг 4: Проверка выборочных записей

```bash
# Проверка наличия ключевых записей (пример)
kubectl exec -n aither-restore-test postgres-test -- \
    psql -U aither -d aither -c \
    "SELECT COUNT(*) FROM users;"

kubectl exec -n aither-restore-test postgres-test -- \
    psql -U aither -d aither -c \
    "SELECT id, created_at FROM models ORDER BY created_at DESC LIMIT 5;"
```

#### Шаг 5: Очистка

```bash
# Немедленное удаление временной среды после проверки
kubectl delete namespace aither-restore-test --wait
```

### 8.2. Периодичность

Test restore должен выполняться **ежемесячно** для одного случайно выбранного daily-бэкапа. Результаты логируются.

### 8.3. Known Limitation

**Полный DR drill (восстановление всего кластера «с нуля» на чистой инфраструктуре) НЕ выполнялся.** Test restore проверяет целостность данных на уровне PostgreSQL, но не верифицирует полную процедуру Disaster Recovery из раздела 11. Проведение полного DR drill запланировано на следующую итерацию после стабилизации инфраструктуры.

---

## 9. Восстановление PV/PVC (Persistent Volume Recovery)

### 9.1. Инвентаризация PV/PVC

Перед любыми операциями восстановления необходимо составить актуальный список PV и PVC:

```bash
# Список всех PVC в namespace
kubectl get pvc -n aither-inference

# Список всех PV
kubectl get pv

# Детальная информация по каждому PVC
kubectl describe pvc -n aither-inference

# Проверка StorageClass
kubectl get storageclass
```

### 9.2. Важные параметры

| Параметр | Значение | Примечание |
|----------|----------|------------|
| StorageClass | Зависит от провайдера (уточняется) | Определяет, поддерживаются ли volume snapshots |
| reclaimPolicy | `Retain` (рекомендуется) | `Delete` приведёт к потере данных при удалении PVC |
| volumeBindingMode | `WaitForFirstConsumer` или `Immediate` | Влияет на порядок восстановления |

### 9.3. Порядок восстановления PVC

1. Убедиться, что `reclaimPolicy` установлен в `Retain` для всех критических PV
2. При наличии поддержки CSI snapshot — восстановить из снапшота
3. При отсутствии снапшотов — пересоздать PVC и восстановить данные из бэкапа PostgreSQL (для БД) или из файловых бэкапов (для файловых PV)

```bash
# Проверка reclaimPolicy для PV
kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.persistentVolumeReclaimPolicy}{"\n"}{end}'

# Изменение reclaimPolicy на Retain (если был Delete)
kubectl patch pv <pv-name> -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
```

### 9.4. Volume Snapshots (если поддерживаются CSI)

```bash
# Проверка доступных VolumeSnapshotClass
kubectl get volumesnapshotclass

# Создание снапшота
kubectl create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: aither-db-snapshot-20260726
  namespace: aither-inference
spec:
  volumeSnapshotClassName: <snapshot-class-name>
  source:
    persistentVolumeClaimName: <pvc-name>
EOF

# Восстановление PVC из снапшота
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: aither-db-restored
  namespace: aither-inference
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: <size>
  dataSource:
    name: aither-db-snapshot-20260726
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
EOF
```

### 9.5. Known Limitation

На стадии Controlled Beta поддержка CSI snapshot зависит от используемого storage-провайдера. Если снапшоты не поддерживаются, восстановление выполняется из логических бэкапов (pg_dump / файловые копии). Полная инвентаризация PV/PVC с документированием StorageClass и reclaimPolicy должна быть выполнена до первого инцидента.

---

## 10. Восстановление Secrets (Secret Recovery)

### 10.1. Запрет на хранение в Git

**Категорически запрещено** коммитить незашифрованные Secret YAML-файлы в Git-репозиторий. Даже в тестовых ветках. Даже временно. Нарушение этого правила создаёт риск компрометации учётных данных при любом доступе к репозиторию (включая историю коммитов).

### 10.2. Обязательное шифрование

Все Secrets перед хранением на диске должны быть зашифрованы (см. раздел 5). Процедура восстановления:

```bash
# 1. Расшифровать Secret из бэкапа
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -in /backup/secret-aither-bff-auth-20260726.yaml.enc \
    -out /tmp/secret-aither-bff-auth-20260726.yaml \
    -pass file:/backup/.backup_key

# 2. Применить Secret в кластер
kubectl apply -f /tmp/secret-aither-bff-auth-20260726.yaml

# 3. Перезапустить зависимые поды
kubectl rollout restart deployment/aither-bff -n aither-inference

# 4. НЕМЕДЛЕННО удалить расшифрованный файл
shred -u /tmp/secret-aither-bff-auth-20260726.yaml
```

### 10.3. Контроль доступа

- Доступ к зашифрованным файлам Secrets ограничен учётной записью `root` (права `600`)
- Ключ шифрования (`/backup/.backup_key`) доступен только `root` (права `600`)
- Доступ к off-site копиям Secrets ограничен отдельной учётной записью

### 10.4. Ротация после восстановления

После восстановления Secrets из бэкапа **обязательно** выполнить ротацию всех учётных данных:

- Пароли БД
- API-ключи (vLLM, внешние сервисы)
- JWT-секреты и сессионные ключи
- Токены доступа к внешним API

Ротация должна быть выполнена в течение 24 часов после восстановления.

### 10.5. Аудит доступа к бэкапам Secrets

```bash
# Логирование каждого доступа к зашифрованным Secret-бэкапам
echo "$(date -Iseconds) | $(whoami) | DECRYPT | secret-aither-bff-auth-20260726.yaml.enc" \
    >> /var/log/backup-secret-access.log

# Логирование каждого применения Secrets
echo "$(date -Iseconds) | $(whoami) | APPLY | secret-aither-bff-auth-20260726.yaml" \
    >> /var/log/backup-secret-access.log

# Права на лог-файл — только root
chmod 600 /var/log/backup-secret-access.log
chattr +a /var/log/backup-secret-access.log  # append-only
```

Все операции с Secret-бэкапами (расшифровка, применение, удаление) должны фиксироваться в аудиторском журнале `/var/log/backup-secret-access.log`, защищённом от модификации (`chattr +a`).

---

## 11. Восстановление (Restore)

### PostgreSQL

```bash
# VPS2 Portal DB
ssh vps2 "psql -U portal -h 127.0.0.1 portal < /backup/portal_db_YYYYMMDD.sql"

# K8s Aither DB
kubectl exec -n aither-inference deployment/postgres -i -- psql -U aither aither < /backup/aither_db_YYYYMMDD.sql
```

### ConfigMaps

```bash
kubectl apply -f /backup/cm-aither-portal-config-YYYYMMDD.yaml
kubectl rollout restart deployment/aither-portal -n aither-inference
```

### Secrets

```bash
# Secrets восстанавливаются из ЗАШИФРОВАННЫХ бэкапов (см. раздел 5 и 10)
kubectl apply -f /backup/secret-aither-bff-auth-YYYYMMDD.yaml
kubectl rollout restart deployment/aither-bff -n aither-inference
```

---

## 12. Disaster Recovery

При полной потере кластера:

1. Развернуть K8s кластер заново
2. Применить все Secrets (из зашифрованных бэкапов, с предварительной расшифровкой)
3. Применить все ConfigMaps
4. Развернуть компоненты в порядке: vLLM → Redis → AI Platform → Identity → BFF → Portal
5. Восстановить PostgreSQL из дампа (с предварительной проверкой sha256sum)
6. Проверить доступность портала и моделей

---

## 13. Контрольный список (Checklist)

### Ежедневно

- [ ] Выполнены все плановые бэкапы (PostgreSQL, ConfigMaps)
- [ ] Secrets зашифрованы, оригиналы удалены
- [ ] Вычислены и сохранены контрольные суммы (sha256sum)
- [ ] Бэкапы скопированы на off-site хранилище

### Еженедельно

- [ ] Проверка целостности всех бэкапов (sha256sum -c)
- [ ] Создан weekly-снапшот

### Ежемесячно

- [ ] Выполнен test restore во временную среду
- [ ] Создан monthly-снапшот
- [ ] Проверена актуальность ключа шифрования
- [ ] Проверен доступ к off-site хранилищу
- [ ] Ротированы устаревшие бэкапы согласно retention policy

### При изменении конфигурации

- [ ] Обновлены бэкапы Secrets и ConfigMaps
- [ ] Secrets зашифрованы немедленно после создания YAML

---

> **Последнее обновление:** 26 июля 2026, ревизия U1.3-OPS-R2
