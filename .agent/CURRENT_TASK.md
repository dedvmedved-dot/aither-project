# AITHER URGENT — Qwen3.8-27B-FP8 Permanent Cutover R1

## 0. Архитектурное решение

OWNER + Architect утвердили постоянную конфигурацию:

- вывести из постоянной эксплуатации `qwen2.5-32b-instruct` на n7;
- оставить без изменений `qwen3-32b` на n8;
- постоянно развернуть на n7 `Qwen/Qwen3.8-27B-FP8` с served id `qwen3.8-27b`;
- после успешного cutover активный каталог Aither должен содержать ровно две модели: `qwen3-32b` и `qwen3.8-27b`;
- обе модели используют существующий entitlement `model:qwen3:chat`;
- новый постоянный auth scope не создавать;
- D2/D3/E1/F1/F2 и остальные roadmap-задачи остаются PAUSED до Architect acceptance этой срочной работы.

Постоянное изменение каталога/routing разрешается только после успешного compatibility gate новой модели на n7.

## 1. Критические требования к поведению Hermes

1. Работать только в данном scope.
2. Не продолжать D2/D3/E1/F1/F2.
3. n8/Qwen3-32B не изменять; только read-only health/smoke validation.
4. Не создавать третью постоянно работающую GPU-модель.
5. Не переходить самовольно на AWQ/GPTQ/NVFP4 при проблеме FP8.
6. Не менять NVIDIA driver, host CUDA, containerd, GPU Operator, CNI, control plane, storage, monitoring, backup, Billing, Identity, users, roles, scopes и DB.
7. Значения существующих Kubernetes Secrets не читать и не выводить. Разрешено только повторно использовать уже существующие Secret references в manifests без разрешения значения.
8. Не создавать API keys, credentials или sessions специально для теста.
9. Hermes не выполняет Git writes: add/commit/push/pull/reset/clean/checkout/switch/merge/rebase/tag/ref mutation запрещены. Commit/push выполняет host runner.
10. `.agent/*` и `/root/.hermes` не изменять.
11. `safe.directory=*`, generic sudo, recursive chown/chmod запрещены.
12. Все изменённые repo-файлы перед завершением должны иметь uid/gid 1000:1000.
13. При непроверяемом gate — fail closed. Если compatibility новой модели не доказана, восстановить Qwen2.5 и вернуть BLOCKED.
14. Не оставлять частичный catalog/routing cutover.
15. Не оставлять n7 без либо принятой Qwen3.8, либо восстановленной Qwen2.5.

## 2. Разрешённые repo paths

Только:

1. `aither-v2/manifests/models/qwen38-27b-fp8.yaml`
2. `aither-v2/services/portal-backend/app/main.py`
3. `aither-v2/services/portal-backend/k8s/portal-backend.yaml`
4. `aither-v2/canonical-image-digests.txt`
5. `docs/evidence/QWEN38_PERMANENT_CUTOVER_R1.md`

Другие repo paths изменять нельзя.

## 3. Preflight — evidence до любых runtime mutations

Зафиксировать:

### Git/governance
- hostname, executor uid/gid, repo ownership;
- branch/HEAD;
- clean worktree;
- task id;
- baseline ancestry;
- diff baseline -> task-control commit.

### n7 hardware
- GPU model/count;
- compute capability;
- total/free VRAM per GPU;
- NVIDIA driver;
- CUDA compatibility доступного container runtime;
- `nvidia-smi` summary/topology;
- доступные Xid/ECC/error indicators.

### Qwen2.5 rollback baseline
Полностью сохранить non-secret эффективное состояние `vllm-32b-instruct-awq`:
- Deployment/Service names;
- replicas;
- image + imageID/digest;
- args;
- node selector/affinity;
- GPU resources;
- volumes/hostPath;
- Service selector/ports;
- probes;
- Ready state;
- model path;
- safe spec/hash data, достаточные для точного rollback.

Secret values не читать.

### n8 invariant
Зафиксировать текущий Ready/image/service state `vllm-qwen3-32b-awq`. Он должен остаться неизменным.

### Storage
Проверить место на n7 для официального snapshot `Qwen/Qwen3.8-27B-FP8` в `/data/models/Qwen3.8-27B-FP8` с operational reserve. Не удалять веса Qwen2.5 для освобождения места.

## 4. Traffic drain

Перед scale-down Qwen2.5 проверить доступные request/in-flight metrics и безопасные application logs минимум за последние 15 минут без request bodies и credentials.

OWNER уже утвердил permanent retirement Qwen2.5, поэтому исторический traffic не блокирует замену. Если в момент cutover есть in-flight request, выполнить bounded graceful drain, если механизм поддерживается, и только после этого scale down.

## 5. vLLM gate

Текущий vLLM 0.8.5 для Qwen3.8 не использовать.

Целевой baseline: официальный `vllm/vllm-openai:v0.27.1`, обязательно pinned immutable digest.

До освобождения n7:
1. определить exact image digest;
2. проверить совместимость container CUDA runtime с установленным driver n7;
3. host driver не обновлять;
4. при наличии штатного Aither mirror workflow разрешён mirror в `10.129.13.78:5000` с сохранением provenance/digest;
5. `latest` и unpinned mutable image запрещены;
6. если download/mirror требует недоступной авторизации — OWNER_REQUIRED, не извлекать credentials из существующих Secrets.

## 6. Official model artifact

Источник: `Qwen/Qwen3.8-27B-FP8`.

Скачать официальный публичный HF snapshot на n7 в `/data/models/Qwen3.8-27B-FP8`.

Зафиксировать:
- exact repo;
- exact revision/commit;
- фактический размер;
- `architectures`, `model_type`;
- quantization configuration;
- safetensors index/shard metadata и безопасные hashes, достаточные для воспроизводимости.

`config.json` не модифицировать. HF token не использовать, если public repository доступен anonymous. Если неожиданно требуется credential — OWNER_REQUIRED.

## 7. FP8 / Turing compatibility gate

n7 = Turing sm_75. Native FP8 tensor acceleration отсутствует.

Допустимый режим — официальный FP8 checkpoint, который vLLM обслуживает на Turing как поддерживаемый weight-only W8A16/Marlin backend.

Не заявлять native FP8 acceleration.

До permanent integration runtime evidence должен доказать, что vLLM принимает официальный checkpoint на sm_75 с поддерживаемым backend.

При unsupported architecture/FP8/Marlin/kernel, compute-capability refusal, illegal instruction, fatal CUDA error, unrecoverable OOM или TP failure: восстановить Qwen2.5, RESULT=BLOCKED, STOP. Alternate quantization не использовать.

## 8. Controlled n7 replacement — compatibility phase

1. Сохранить rollback baseline Qwen2.5.
2. Gracefully scale `vllm-32b-instruct-awq` to 0.
3. Проверить освобождение обеих GPU n7.
4. Не удалять Qwen2.5 Deployment/Service/weights в R1: после финального успеха оставить как rollback asset, но non-serving/scale 0.
5. n8 не трогать.

Создать новый authoritative manifest:
`aither-v2/manifests/models/qwen38-27b-fp8.yaml`

Runtime contract:
- namespace `aither-inference`;
- Deployment `vllm-qwen38-27b-fp8`;
- Service `vllm-qwen38-27b-fp8`;
- node n7 only;
- 2 GPUs;
- model `/data/models/Qwen3.8-27B-FP8`;
- served model `qwen3.8-27b`;
- TP=2.

Initial baseline args:
- `--tensor-parallel-size 2`
- `--gpu-memory-utilization 0.90`
- `--max-model-len 8192`
- `--max-num-seqs 1`
- `--enforce-eager`
- `--served-model-name qwen3.8-27b`

Использовать checkpoint quantization metadata / vLLM autodetection. `--quantization fp8` не добавлять механически; explicit argument допустим только если vLLM 0.27.1 требует его для этого exact checkpoint и причина доказана.

Не использовать неподтверждённый `--language-model-only`. Работать обычным generative serving и отправлять text-only requests.

Не включать в baseline: speculative decoding, MTP, FP8 KV cache, prefix-caching tuning, tool calling, image/video requests, custom CUDA-graph tuning, 64K/262K/1M context.

Если существующие vLLM deployments используют API-key через Secret, повторно использовать тот же Secret reference по существующему шаблону, но значение Secret не читать.

## 9. Direct compatibility tests до catalog mutation

Новый pod должен быть Running/Ready, без OOMKilled/CrashLoop/fatal CUDA.

Evidence:
- vLLM version + immutable image digest;
- PyTorch/CUDA versions;
- actual quantization/backend selection;
- TP initialization;
- load time;
- VRAM per GPU;
- restart count.

Через direct Service:
- GET `/health` -> 200;
- GET `/v1/models` -> `qwen3.8-27b`;
- POST `/v1/chat/completions` -> 200 text response.

Functional matrix:
- Russian;
- English;
- code generation;
- stream=false;
- stream=true clean termination;
- malformed request -> controlled 4xx;
- invalid model -> controlled 4xx;
- over-context request -> controlled 4xx, pod remains healthy;
- pod restart -> Ready restored.

Thinking/reasoning параметры тестировать только если они документированно поддерживаются фактически установленной связкой Qwen3.8/vLLM. Не патчить framework ради неподдерживаемого поведения.

## 10. Context escalation

8192 — обязательный PASS baseline.
После стабильного 8192 проверить 16384.
32768 — только при доказанном VRAM reserve.

Финальный production manifest использует максимальный прошедший stability gate context, но не выше 65536 в R1. 262144/1M — OUT OF SCOPE.

## 11. Performance evidence

После отдельного warm-up выполнить минимум 5 сопоставимых запросов и собрать:
- TTFT, если доступен;
- prompt/completion tokens;
- generation tokens/sec;
- end-to-end latency;
- GPU memory/utilization;
- `vllm:gpu_cache_usage_perc`, если есть;
- CPU RAM;
- restart count;
- request success/failure.

Это compatibility/stability, не tuning task.

## 12. Rollback при compatibility failure

До catalog cutover при любом FAIL:
1. остановить/удалить failed Qwen3.8 workload по необходимости;
2. восстановить `vllm-32b-instruct-awq` точно к captured preflight state;
3. дождаться Ready;
4. smoke-test Qwen2.5 direct service;
5. проверить Qwen3-32B n8;
6. записать evidence;
7. RESULT=BLOCKED;
8. STOP.

Portal catalog/routing при failed compatibility не менять.

## 13. Permanent portal-backend integration — только после compatibility PASS

Обновить production contract ровно до двух моделей:
- `qwen3-32b`
- `qwen3.8-27b`

В `app/main.py`:
1. удалить `qwen2.5-32b-instruct` из active `ALLOWED_MODELS` и active model-list contracts;
2. удалить Qwen2.5 из active `CURRENT_MODELS`;
3. добавить `qwen3.8-27b` со scope `model:qwen3:chat`;
4. оставить `qwen3-32b` со scope `model:qwen3:chat`;
5. убрать active substring routing вида `if "qwen3" in model`;
6. реализовать explicit exact-model mapping;
7. неизвестная модель -> controlled 4xx/model_not_found до upstream;
8. internal portal chat и external OpenAI-compatible API должны использовать один и тот же exact two-model contract там, где применимо.

Явные upstreams:
- `qwen3-32b` -> `http://vllm-qwen3-32b-awq.aither-inference.svc:8000`
- `qwen3.8-27b` -> `http://vllm-qwen38-27b-fp8.aither-inference.svc:8000`

Рекомендуемые env names либо столь же явные аналоги:
- `UPSTREAM_QWEN3_32B_URL/TOKEN`
- `UPSTREAM_QWEN38_27B_URL/TOKEN`

В `portal-backend/k8s/portal-backend.yaml` добавить exact URLs и существующие Secret references, не читая Secret values. Не оставлять `UPSTREAM_14B/UPSTREAM_32B` substring heuristic как production decision mechanism.

## 14. Portal backend build/deploy

Использовать существующий build procedure, не меняя build-system files.

Собрать новый portal-backend image, опубликовать через штатный Aither registry workflow и зафиксировать immutable digest/task-specific immutable tag + verified digest. Registry credentials не выводить и не извлекать из Secrets. Если штатный workflow невозможен без неразрешённого secret access — OWNER_REQUIRED.

Deploy только изменения portal-backend, необходимые для explicit mapping. Дождаться Ready и проверить `/health`.

Обновить `aither-v2/canonical-image-digests.txt` только новыми фактическими digest/provenance для:
- Qwen3.8 vLLM image;
- нового portal-backend image.

## 15. External path gate без credentials

В R1 credential creation/access запрещён. Поэтому проверить доступное без секрета:

- Test Zone `GET /health` -> 200;
- `POST /api/v1/chat/completions` без Authorization -> 401/403, не 404/5xx;
- `GET /api/v1/models` без Authorization -> ожидаемый auth failure, не 404/5xx;
- source/runtime contract в portal-backend содержит ровно две approved model entries;
- direct Qwen3.8 Service chat -> 200;
- direct Qwen3-32B Service health/chat smoke -> PASS, если это возможно без чтения credential; если direct service требует secret token, health + Ready + existing safe metrics/log evidence достаточны для R1 n8 invariant.

Не создавать credential для превращения R1 в authenticated E2E.

После PASS R1 Architect отдельно опубликует узкий R1B authenticated E2E gate с безопасно ограниченным lifecycle test credential либо другим approved auth mechanism.

## 16. Final state R1

n7:
- `vllm-qwen38-27b-fp8` replicas=1, Ready, permanent;
- `vllm-32b-instruct-awq` non-serving/replicas=0 и сохранён как rollback asset.

n8:
- `vllm-qwen3-32b-awq` unchanged, Ready.

Portal/API source/runtime:
- active model ids exactly `qwen3-32b`, `qwen3.8-27b`;
- both scope `model:qwen3:chat`;
- exact explicit model->upstream mapping;
- Qwen2.5 не advertised в active contract и не имеет active routing path.

Security:
- no new credentials;
- no Secret values read;
- no DB mutations;
- no Hermes Git writes;
- no out-of-scope mutations.

## 17. Evidence

Создать `docs/evidence/QWEN38_PERMANENT_CUTOVER_R1.md` и включить:
1. preflight governance;
2. hardware/driver/CUDA;
3. Qwen2.5 rollback baseline;
4. n8 before/after invariant;
5. HF repo exact revision/model metadata;
6. vLLM immutable image digest/provenance;
7. actual FP8/Turing backend proof;
8. model artifact size/hash metadata;
9. authoritative manifest summary;
10. startup logs sanitized;
11. context gates;
12. performance table;
13. negative tests;
14. explicit routing/source diff summary;
15. portal-backend image digest;
16. Kubernetes rollout state;
17. final source/runtime active model ids;
18. unauthenticated external route status checks;
19. exact runtime mutations;
20. exact changed repo paths;
21. ownership/modes;
22. `git diff --check` and final worktree state;
23. secret scan.

Summary fields:
- `FINAL_MODEL_SET: qwen3-32b,qwen3.8-27b`
- `QWEN25_RETIRED: YES|NO`
- `QWEN38_READY: YES|NO`
- `QWEN38_DIRECT_CHAT_200: YES|NO`
- `QWEN3_32B_HEALTHY: YES|NO`
- `EXTERNAL_ROUTES_PRESENT: YES|NO`
- `AUTHENTICATED_E2E: DEFERRED_R1B`
- `FP8_TURING_BACKEND: <value>`
- `DB_MUTATION: NONE|<details>`
- `SECRET_VALUES_READ: NO|YES`
- `OUT_OF_SCOPE_MUTATION: NONE|<details>`
- `OWNERSHIP_GATE: PASS|FAIL`
- `SECRETS_EXPOSED: NO|YES`
- `FINAL_GATE: PASS|BLOCKED|OWNER_REQUIRED`

## 18. PASS / BLOCKED

R1 PASS только если:
- official Qwen3.8 FP8 стабильно работает на n7 Turing TP=2;
- supported FP8 backend доказан;
- выбранный context gate стабилен;
- direct Qwen3.8 inference 200;
- permanent Qwen3.8 deployment Ready;
- n8 Qwen3-32B остаётся healthy;
- portal/backend active contract содержит ровно две approved модели;
- используется explicit exact routing, без substring fallback;
- Qwen2.5 отсутствует из active model contract;
- external routes существуют и fail with auth semantics rather than 404/5xx when unauthenticated;
- no credential/DB/secret mutation;
- source/runtime state воспроизводим из разрешённых paths;
- только разрешённые repo paths изменены;
- ownership gate PASS.

Authenticated external 200 для обеих моделей НЕ является R1 PASS criterion и будет отдельным R1B gate. R1 не считается FINAL PRODUCT ACCEPTANCE без R1B.

При compatibility fail — восстановить Qwen2.5 и BLOCKED.
При fail после catalog mutation — rollback portal/backend/catalog и Qwen2.5 к pre-task state перед BLOCKED, если технически возможно; остаточное состояние подробно зафиксировать.

Hermes не может self-accept. Architect acceptance required.
