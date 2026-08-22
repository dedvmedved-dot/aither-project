# AITHER-URGENT-QWEN38-DOWNLOAD-VERIFY-N7-R1

## Цель
Только read-only проверить текущее состояние загрузки `Qwen/Qwen3.8-27B-FP8` на n7 после orphaned `hf download`. Ничего не менять в runtime, не запускать и не останавливать процессы, не трогать Kubernetes.

## Проверить
1. Существует ли процесс `hf download Qwen/Qwen3.8-27B-FP8` на n7.
2. Размер `/data/models/Qwen3.8-27B-FP8`.
3. Exact revision из локального snapshot/кеша и/или командной строки процесса.
4. Прочитать `model.safetensors.index.json` и определить точное число ожидаемых shard-файлов.
5. Сосчитать фактически присутствующие shard-файлы и перечислить отсутствующие.
6. Найти `.incomplete`, `.lock`, `.partial`, temporary download artifacts.
7. Проверить, что config/tokenizer/index files читаются.
8. Если все ожидаемые shard-файлы присутствуют и нет incomplete artifacts — зафиксировать DOWNLOAD_COMPLETE=YES.
9. Если не все файлы присутствуют — DOWNLOAD_COMPLETE=NO и зафиксировать progress без каких-либо изменений.
10. Не читать secrets, токены, env dumps.
11. Не выполнять Git writes; host runner выполняет commit/push.

## Evidence
Создать только `docs/evidence/QWEN38_DOWNLOAD_VERIFY_N7_R1.md` с фактами, временем замера и итогом.

## PASS
PASS означает, что проверка выполнена достоверно. Внутри evidence отдельно указывать `DOWNLOAD_COMPLETE=YES|NO`.

После evidence STOP. Никакого vLLM, Deployment/Service, catalog/routing, scale операций или продолжения cutover.
