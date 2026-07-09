.PHONY: help deploy test docs bundle offline-load clean check

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check: ## Проверить наличие зависимостей (ansible, kubectl, docker)
	@echo "=== Проверка зависимостей ==="
	@command -v ansible-playbook >/dev/null 2>&1 || { echo "❌ ansible не установлен"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl не установлен"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "❌ docker не установлен"; exit 1; }
	@echo "✅ Все зависимости установлены"

deploy: check ## Развернуть платформу (ansible-playbook site.yml)
	@echo "=== Развёртывание Aither Platform ==="
	cd playbooks && ansible-playbook -i inventory.yml site.yml

test: ## Приёмо-сдаточные тесты
	@echo "=== Приёмо-сдаточные тесты ==="
	@bash tests/01-smoke.sh || { echo "❌ Smoke tests FAILED"; exit 1; }
	@echo "✅ Smoke: OK"
	@bash tests/02-api.sh || { echo "❌ API tests FAILED"; exit 1; }
	@echo "✅ API: OK"
	@bash tests/03-security.sh || { echo "❌ Security tests FAILED"; exit 1; }
	@echo "✅ Security: OK"
	@echo "=== Все тесты пройдены ==="

test-smoke: ## Только дымовые тесты
	bash tests/01-smoke.sh

test-api: ## Только API-тесты
	bash tests/02-api.sh

test-security: ## Только тесты безопасности
	bash tests/03-security.sh

docs: ## Открыть документацию (показать список)
	@echo "=== Документация ==="
	@ls -1 docs/*.md

bundle: ## Собрать офлайн-пакет (docker save + pip download)
	@echo "=== Сборка офлайн-пакета ==="
	@echo "Сохраняем Docker-образы..."
	bash offline/docker/save.sh
	@echo "Скачиваем pip-пакеты..."
	bash offline/pip/download.sh
	@echo "Генерируем контрольные суммы..."
	cd offline && find . -type f ! -name checksums.sha256 -exec sha256sum {} \; > checksums.sha256
	@echo "✅ Пакет собран: offline-deploy/"

offline-load: ## Загрузить офлайн-зависимости на целевую машину
	@echo "=== Загрузка офлайн-зависимостей ==="
	bash offline/docker/load.sh
	bash offline/pip/install.sh
	@echo "✅ Зависимости загружены"

backup: ## Резервное копирование (БД, конфиги)
	bash scripts/backup.sh

restore: ## Восстановление из бэкапа
	bash scripts/restore.sh

clean: ## Очистить временные файлы
	@echo "=== Очистка ==="
	rm -f offline/docker/images.tar.gz
	rm -rf offline/pip/packages/
	rm -f offline/checksums.sha256
	@echo "✅ Очищено"

verify: ## Проверить контрольные суммы
	@echo "=== Проверка контрольных сумм ==="
	cd offline && sha256sum -c checksums.sha256

version: ## Показать версию
	@cat VERSION
