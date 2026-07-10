# Часть III. Разработка и доработка

> **Документ 3 из 5.** Как изменять, расширять и улучшать платформу: код, модели, автоматизация.

---

# Глава 14. Инструменты разработчика

> **Цель главы:** освоить базовые инструменты, необходимые для доработки платформы: Git, VS Code, Python и Node.js/TypeScript на минимально необходимом уровне.

---

## 14.1. Git — система контроля версий

**Git** — это «машина времени» для кода. Он запоминает каждое изменение, позволяет вернуться назад и работать параллельно над разными задачами.

### Основные понятия

| Термин | Что значит | Аналогия |
|---|---|---|
| **Репозиторий** (repo) | Папка с кодом + вся история изменений | Папка проекта |
| **Коммит** (commit) | Снимок состояния всех файлов | «Сохранить» в игре |
| **Ветка** (branch) | Параллельная версия кода | Отдельная вселенная |
| **Remote** | Копия репозитория на сервере (GitHub) | Облачное хранилище |
| **Pull request** | Запрос на слияние изменений | «Начальник, прими мои правки» |

### Рабочий цикл

```bash
# 1. Клонируем репозиторий (один раз)
git clone git@github.com:dedvmedved-dot/aither-project.git
cd aither-project

# 2. Создаём ветку для задачи
git checkout -b fix/toLocaleString-error

# 3. Вносим изменения...
vim portal/static/admin.html

# 4. Смотрим, что изменилось
git status
git diff portal/static/admin.html

# 5. Добавляем изменения в коммит
git add portal/static/admin.html

# 6. Создаём коммит
git commit -m "fix: проверка d.error перед toLocaleString"

# 7. Отправляем на GitHub
git push origin fix/toLocaleString-error

# 8. Создаём Pull Request на GitHub → принимаем → сливаем в main

# 9. Возвращаемся в main и подтягиваем изменения
git checkout main
git pull
```

### Основные команды — шпаргалка

| Команда | Назначение |
|---|---|
| `git status` | Что изменилось? |
| `git diff` | Что именно изменилось? |
| `git add <файл>` | Добавить в коммит |
| `git commit -m "..."` | Создать коммит |
| `git push` | Отправить на сервер |
| `git pull` | Забрать с сервера |
| `git log --oneline` | История коммитов |
| `git checkout <ветка>` | Переключить ветку |
| `git branch` | Список веток |

---

## 14.2. Среда разработки

**VS Code** — основной редактор. Главная фишка для нас: **Remote-SSH**. Вы подключаетесь к серверу по SSH и редактируете файлы так, как будто они локальные.

```bash
# В VS Code: Ctrl+Shift+P → Remote-SSH: Connect to Host → root@10.129.13.78
# Открываете папку /root/aither-project — и работаете!
```

Если VS Code недоступен — **nano** в терминале:
```
Ctrl+O — сохранить
Ctrl+X — выйти
Ctrl+W — поиск
Ctrl+K — вырезать строку
Ctrl+U — вставить
```

**SSH-туннели** для доступа к K8s-сервисам:
```bash
# Пробросить порт Grafana локально
ssh -L 30300:10.129.13.77:30300 root@VPS1_IP
# Теперь http://localhost:30300 → Grafana!
```

**kubectl port-forward** — то же самое, но через K8s:
```bash
kubectl port-forward svc/gateway 8080:8080
# http://localhost:8080 → Gateway
```

---

## 14.3. Python — ликбез для доработки Gateway

Gateway написан на Python. Чтобы дорабатывать его, нужно знать минимум.

**Базовый синтаксис:**
```python
# Переменные
name = "Aither"
port = 8080
models = ["14b", "32b"]

# Функции
def check_balance(org_id: str) -> int:
    """Проверить баланс организации. Возвращает количество токенов."""
    result = db.query(f"SELECT balance FROM billing WHERE org_id='{org_id}'")
    return result[0] if result else 0

# Условия
if balance <= 0:
    raise HTTPException(402, "Insufficient tokens")

# Циклы
for model in models:
    print(f"Model: {model}")

# Импорты
from gateway.billing import deduct_tokens
from gateway.dlp import check_dlp
```

**Виртуальное окружение (venv):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r gateway/requirements.txt
```

**Типовые ошибки:**
- `IndentationError` — кривые отступы (Python использует отступы вместо скобок!)
- `NameError: name 'x' is not defined` — переменная не объявлена
- `TypeError: can't multiply sequence by non-int` — перепутали типы
- `ModuleNotFoundError: No module named 'redis'` — забыли `pip install`

---

## 14.4. Node.js/TypeScript — ликбез для доработки портала

BFF портала написан на TypeScript. Минимальные знания:

```typescript
// Переменные с типами
const PORT: number = 3000;
const secret: string = process.env.JWT_SECRET || 'dev-secret';

// Интерфейсы (описание формы данных)
interface User {
  email: string;
  org_id: string;
  role: 'admin' | 'org_admin' | 'user';
}

// Асинхронные функции (async/await)
async function getUser(email: string): Promise<User | null> {
  const result = await db.query('SELECT * FROM users WHERE email = $1', [email]);
  return result.rows[0] || null;
}

// Express-роуты
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});
```

**Компиляция:**
```bash
npm install          # установить зависимости
npx tsc              # скомпилировать TypeScript → JavaScript
node dist/server.js  # запустить
```


# Глава 15. Доработка Gateway

> **Цель:** научиться добавлять модели, менять тарифы, добавлять DLP-правила и деплоить изменения.

---

## 15.1. Добавление новой модели

Шаг 1 — добавить модель в каталог (`configs/k8s/gateway-catalog.yaml`):

```yaml
- name: qwen2.5-coder-14b
  display_name: "Qwen 2.5 Coder 14B"
  backend: "http://vllm-coder:8000"
  max_tokens: 4096
  tokens_per_ruble: 100
  tags: [code, fast]
  status: active
```

Шаг 2 — применить:
```bash
kubectl create configmap gateway-catalog \
  --from-file=catalog.yaml=configs/k8s/gateway-catalog.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deploy/gateway
```

Шаг 3 — проверить:
```bash
curl http://gateway:8080/v1/models | jq '.data[].id'
# → "qwen2.5-14b"
# → "qwen2.5-32b"
# → "qwen2.5-coder-14b"  ← новая!
```

## 15.2. Изменение тарифов

Тарифы задаются переменными окружения:
```bash
kubectl set env deploy/gateway TOKEN_COST=***      # цена токена
kubectl set env deploy/gateway RATE_LIMIT_RPM=500   # запросов/мин
# Эффект мгновенный (без рестарта!)
```

## 15.3. Добавление DLP-правила

В `gateway/dlp.py` добавляем правило:

```python
# Номер банковской карты: 16 цифр группами по 4
(re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), 'банковская карта', 'BLOCK'),
```

Деплой:
```bash
docker build -t gateway:latest -f gateway/Dockerfile .
docker push localhost:5000/gateway:latest
kubectl rollout restart deploy/gateway
```

## 15.4. Деплой изменений: полный цикл

```bash
# 1. Изменили код
# 2. Закоммитили
git add -A && git commit -m "feat: новое DLP-правило для карт"

# 3. Собрали образ
docker build -t ghcr.io/.../gateway:latest -f gateway/Dockerfile .

# 4. Запушили
docker push ghcr.io/.../gateway:latest

# 5. Обновили деплоймент
kubectl set image deploy/gateway gateway=ghcr.io/.../gateway:latest

# 6. Проверили
kubectl rollout status deploy/gateway
curl http://gateway:8080/health

# 7. Если что-то пошло не так — откат
kubectl rollout undo deploy/gateway
```


# Глава 16. Доработка портала

> **Цель:** изменять фронтенд, добавлять страницы, подключать OAuth-провайдеров.

---

## 16.1. Изменение фронтенда

Вся статика в `portal/static/`. Меняем, например, цветовую схему:

```css
/* Было: */
.header { background: #1a1a2e; }

/* Стало: */
.header { background: #0d47a1; }  /* синий Astra Linux */
```

Деплой фронтенда — копируем файл (без рестарта BFF!):
```bash
scp portal/static/index.html root@130.17.1.90:/opt/aither/static/
# Готово! Пользователи видят новую тему после обновления страницы.
```

## 16.2. Добавление страницы

Шаг 1 — HTML-файл (`portal/static/api-keys.html`)
Шаг 2 — роут в BFF (`server.ts`): `app.get('/api-keys', (req, res) => res.sendFile(...))`
Шаг 3 — деплой: `scp` статику + `systemctl restart aither-bff`

## 16.3. OAuth-провайдер

Подключение нового провайдера (например, VK):
1. Регистрация приложения на vk.com → `client_id` + `client_secret`
2. Роуты в `server.ts`: `/auth/vk` + `/auth/vk/callback`
3. Добавить в `.env`: `VK_CLIENT_ID`, `VK_CLIENT_SECRET`


# Глава 17. LoRA-адаптеры

> **Цель:** подготовить датасет, обучить LoRA-адаптер на своих данных.

---

## 17.1. Подготовка датасета

Формат — JSONL (один пример = одна строка):
```json
{"messages": [{"role": "system", "content": "Ты — эксперт по Astra Linux."}, {"role": "user", "content": "Как установить пакет?"}, {"role": "assistant", "content": "apt-get install <имя_пакета>"}]}
```

Минимум 20-30 примеров. Лучше 100+.

## 17.2. Запуск обучения

```bash
python3 fine-tuning/train_lora_14b.py \
  --model /models/Qwen2.5-14B-Instruct \
  --dataset my-data.jsonl \
  --output /models/lora-my-adapter \
  --rank 8 --epochs 3
```

На одной RTX 6000: 10-30 минут на 100 примерах.

## 17.3. Подключение к vLLM

```bash
cp -r /models/lora-my-adapter /data/models/
kubectl set env deploy/vllm-qwen \
  "LORA_MODULES=my-adapter=/models/lora-my-adapter/"
kubectl rollout restart deploy/vllm-qwen
```


# Глава 18. CI/CD и автоматизация

> **Цель:** настроить автоматическую сборку и деплой при каждом git push.

---

## 18.1. GitHub Actions workflow

Файл `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy Gateway
on:
  push:
    branches: [main]
    paths:
      - 'gateway/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t ghcr.io/${{ github.repository }}-gateway:${{ github.sha }} -f gateway/Dockerfile .

      - name: Push to ghcr.io
        run: |
          echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/${{ github.repository }}-gateway:${{ github.sha }}

      - name: Deploy to K8s
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS2_HOST }}
          key: ${{ secrets.VPS2_SSH_KEY }}
          script: |
            kubectl set image deploy/gateway gateway=ghcr.io/${{ github.repository }}-gateway:${{ github.sha }}
            kubectl rollout status deploy/gateway

      - name: Health check
        run: |
          for i in $(seq 5); do
            curl -sf http://${{ secrets.VPS2_HOST }}:30900/health && break
            sleep 5
          done

      - name: Notify Telegram
        if: always()
        uses: appleboy/telegram-action@v1
        with:
          to: ${{ secrets.TELEGRAM_CHAT_ID }}
          token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          message: |
            🚀 Gateway deployed!
            Status: ${{ job.status }}
            Commit: ${{ github.sha }}
```

## 18.2. Необходимые секреты

В GitHub → Settings → Secrets → Actions:
- `GHCR_TOKEN` — токен GitHub Container Registry
- `VPS2_HOST` — IP VPS2
- `VPS2_SSH_KEY` — приватный SSH-ключ
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — для уведомлений

---

**Часть III завершена.** Вы научились:
- Работать с Git (clone → branch → commit → push → PR)
- Редактировать код в VS Code Remote-SSH
- Добавлять модели, менять тарифы, дописывать DLP-правила
- Менять фронтенд портала (мгновенный деплой через scp)
- Обучать LoRA-адаптеры на своих данных
- Настраивать CI/CD (GitHub Actions → автосборка → автодеплой → Telegram)

**Последний документ — Приложения и Лабораторный практикум.**