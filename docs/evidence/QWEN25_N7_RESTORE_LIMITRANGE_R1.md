# Qwen2.5 n7 Restore — LimitRange CPU Alignment R1

## Task / Result
- task_id: `AITHER-URGENT-QWEN25-N7-RESTORE-LIMITRANGE-R1`
- executor: `hermes`
- mode: `NARROW_SOURCE_RUNTIME_RESTORE`
- branch: `aither-v2`
- baseline_sha: `92d15a97a360304cb3066ac626f8b1ae149bb4fb`
- HEAD at execution: `ad234df7477a59e324783633c86d5a991fbd8edb`
- baseline is ancestor of HEAD: **YES** (verified via `git merge-base --is-ancestor`)
- HEAD commit touches only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` (verified via `git show --stat`)
- result: **PASS**

## Timestamps
- execution window: `2026-08-23T06:01Z` – `2026-08-23T06:04Z` UTC (`09:01` – `09:04` MSK)
- evidence collected at: `2026-08-23T06:04Z` UTC

---

## 1. Blocker verification (before fix)

Namespace `aither-inference` LimitRange `aither-limits` (type `Container`):

```yaml
spec:
  limits:
  - type: Container
    max:
      cpu: "8"
      memory: 64Gi
    default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
```

Admission event (repeated, before fix):

```
Warning  FailedCreate  replicaset/vllm-32b-instruct-awq-7fbcb77c99
  Error creating: pods "vllm-32b-instruct-awq-7fbcb77c99-..." is forbidden:
  maximum cpu usage per Container is 8, but limit is 16
```

Pre-fix deployment state: `vllm-32b-instruct-awq` `0/1`, `0` ready/available, `ReplicaFailure=True (FailedCreate)`. No Qwen2.5 pod scheduled on n7. Blocker confirmed to be exactly the LimitRange CPU admission failure; no new blocker observed.

## 2. Before/after CPU resource stanza

Before (committed manifest, baseline `92d15a9`):

```yaml
        resources:
          requests:
            cpu: "8"
            memory: "48Gi"
            nvidia.com/gpu: "2"
          limits:
            cpu: "16"
            memory: "64Gi"
            nvidia.com/gpu: "2"
```

After (only `limits.cpu` changed):

```yaml
        resources:
          requests:
            cpu: "8"
            memory: "48Gi"
            nvidia.com/gpu: "2"
          limits:
            cpu: "8"
            memory: "64Gi"
            nvidia.com/gpu: "2"
```

Only `resources.limits.cpu` for container `vllm` was changed (`"16"` → `"8"`). `requests.cpu`, memory, GPU count, model args, image, service, probes, nodeSelector, and all other fields are untouched (see git diff summary below).

## 3. Apply / rollout result

```
$ kubectl apply -f aither-v2/deploy/vllm-32b-instruct-awq.yaml
deployment.apps/vllm-32b-instruct-awq configured
service/vllm-32b-instruct-awq unchanged

$ kubectl -n aither-inference rollout status deployment/vllm-32b-instruct-awq --timeout=540s
deployment "vllm-32b-instruct-awq" successfully rolled out
```

Deployment `spec.replicas` = `1` (verified). New ReplicaSet `vllm-32b-instruct-awq-64b4dfc657` scaled up 0→1; old ReplicaSet `vllm-32b-instruct-awq-7fbcb77c99` scaled down 1→0. Event `SuccessfulCreate` recorded — no further admission rejection.

## 4. Pod / node / restart state

```
NAME                                     READY   STATUS    RESTARTS   AGE     IP            NODE
vllm-32b-instruct-awq-64b4dfc657-l8sm9   1/1     Running   0          2m23s   10.244.1.81   bootsmam-k8s-clnt01-n7-gpu
```

- pod `vllm-32b-instruct-awq-64b4dfc657-l8sm9`
- node: `bootsmam-k8s-clnt01-n7-gpu` (n7)
- phase `Running`, Ready `True`, restarts `0`

## 5. Health result

```
$ kubectl -n aither-inference exec vllm-32b-instruct-awq-64b4dfc657-l8sm9 -- \
    curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8000/health
HTTP 200
```

## 6. `/v1/models` verification

```
$ kubectl -n aither-inference exec vllm-32b-instruct-awq-64b4dfc657-l8sm9 -- \
    curl -s http://localhost:8000/v1/models
{"error":"Unauthorized"}   (HTTP 401)
```

- `/v1/models` is API-key gated (env `VLLM_API_KEY` sourced from secret `vllm-api-key`). Direct HTTP without the key returns 401.
- `secret_access: false` in task capabilities — secret was NOT read.
- **AUTH_REQUIRED** for direct `/v1/models`; served model name verified instead from the live vLLM startup log (authorized runtime path, no credentials):

```
INFO 08-22 23:01:39 [api_server.py] args: Namespace(... served_model_name=['qwen2.5-32b-instruct'] ...)
INFO 08-22 23:01:54 [llm_engine.py] Initializing a V0 LLM engine (v0.8.5) ... served_model_name=qwen2.5-32b-instruct ...
```

`/health` (mandatory) = HTTP 200.

## 7. GPU allocation on n7

- n7 `nvidia.com/gpu`: capacity `2`, allocatable `2`.
- Restored Qwen2.5 pod requests/limits `nvidia.com/gpu: "2"` and is the only GPU-using pod scheduled on n7:

```
vllm-32b-instruct-awq-64b4dfc657-l8sm9  bootsmam-k8s-clnt01-n7-gpu  limits.nvidia.com/gpu = 2
```

- Both n7 GPUs allocated to the restored Qwen2.5 pod. Model weights loaded: `model weights take 9.01GiB` per worker (tensor-parallel-size 2).

## 8. Absence of qwen38 / compat temporary objects

```
$ kubectl -n aither-inference get deploy,rs,po,svc | grep -iE 'qwen38|compat|27b|fp8'
NONE
```

No `qwen38`/`compat` Deployment, ReplicaSet, Pod, or Service objects remain in `aither-inference`.

## 9. n8 Qwen3 unchanged / health

```
NAME                 READY   UP-TO-DATE   AVAILABLE   AGE
vllm-qwen3-32b-awq   1/1     1            1           12d

NAME                                 READY   STATUS    RESTARTS   AGE   IP             NODE
vllm-qwen3-32b-awq-86cb6c9845-n2xpg  1/1     Running   0          12d  10.244.0.252   bootsman-k8s-clnt01-n8-gpu
```

```
$ kubectl -n aither-inference exec vllm-qwen3-32b-awq-86cb6c9845-n2xpg -- \
    curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8000/health
HTTP 200
```

n8 `vllm-qwen3-32b-awq` remains `1/1` Ready with `/health` 200.

## 10. Git diff summary

```
$ git status --short
 M aither-v2/deploy/vllm-32b-instruct-awq.yaml

$ git diff -- aither-v2/deploy/vllm-32b-instruct-awq.yaml
--- a/aither-v2/deploy/vllm-32b-instruct-awq.yaml
+++ b/aither-v2/deploy/vllm-32b-instruct-awq.yaml
@@ -85,7 +85,7 @@ spec:
             memory: "48Gi"
             nvidia.com/gpu: "2"
           limits:
-            cpu: "16"
+            cpu: "8"
             memory: "64Gi"
             nvidia.com/gpu: "2"
```

Single source change: `limits.cpu` `16` → `8`. No other tracked file modified. No non-codex-owned files created under repo paths touched.

## 11. Security

- SECRETS_EXPOSED: NO
