# Aither MVP RC1 — Verification Matrix

| # | Requirement | Verification Method | Evidence Location | Status |
|---|---|---|---|---|
| **Architecture** | | | | |
| 1 | Gateway exists and serves on port 8000 | `kubectl get svc -n aither-inference nginx-gateway-32b` | manifests | ✅ |
| 2 | 2 gateway replicas (one per node) | `kubectl get pods -n aither-inference -l app=nginx-gateway` | runtime | ✅ |
| 3 | vLLM 32B service accessible | `kubectl get svc -n aither-inference vllm-32b-gptq` | manifests | ✅ |
| 4 | BFF API deployed and serving | `kubectl get pods -n aither-inference -l app=aither-bff` | manifests | ✅ |
| 5 | Portal deployed and serving | `kubectl get pods -n aither-inference -l app=aither-portal` | manifests | ✅ |
| **DNS** | | | | |
| 6 | Gateway pods use ClusterFirst DNS | `kubectl get deployment -n aither-inference nginx-gateway-32b -o jsonpath='{.spec.template.spec.dnsPolicy}'` | Script check 3.11 | ✅ |
| 7 | CoreDNS ClusterIP accessible | `nslookup kubernetes.default.svc.cluster.local` from pod | DNS-N7-EVIDENCE.md | ✅ |
| 8 | External DNS resolution works | `nslookup google.com` from pod | DNS-N7-EVIDENCE.md | ✅ |
| **Authentication** | | | | |
| 9 | Without token → 401 | `curl -s -o /dev/null -w "%{http_code}" http://gateway/v1/completions` | Script check 5 | ✅ |
| 10 | Valid token → 200 | `curl -s -H "Authorization: Bearer <token>" http://gateway/v1/completions` | Script check 6 | ✅ |
| 11 | Wrong token → 401 | `curl -s -H "Authorization: Bearer wrong" http://gateway/v1/completions` | Script check 5 | ✅ |
| 12 | Chat completions blocked | `/v1/chat/completions` → 422 | Script check 5 | ✅ |
| **Model Consistency** | | | | |
| 13 | /v1/models returns actual model ID | `curl -s http://gateway/v1/models -H "Authorization: Bearer <token>"` | Script check 6 | ✅ |
| 14 | /v1/completions returns HTTP 200 | Authenticated completion request | Script check 6 | ✅ |
| 15 | Response model matches requested model | Compare `model` in request vs response | Script check 6 | ✅ |
| 16 | Completion text non-empty | Response `text` field not empty | Script check 6 | ✅ |
| **Health** | | | | |
| 17 | Gateway /healthz returns 200 (local) | `curl -s localhost:8000/healthz` from pod | Script check 4 | ✅ |
| 18 | Gateway /health returns 200 (upstream) | `curl -s localhost:8000/health` from pod | Script check 4 | ✅ |
| 19 | Gateway /healthz on n7 | Via n7 pod | Script check 4 | ✅ |
| 20 | Gateway /health on n7 | Via n7 pod | Script check 4 | ✅ |
| 21 | Gateway /healthz on n8 | Via n8 pod | Script check 4 | ✅ |
| 22 | Gateway /health on n8 | Via n8 pod | Script check 4 | ✅ |
| **Readiness** | | | | |
| 23 | Gateway pods phase=Running | `kubectl get pods -o wide` | Script check 2 | ✅ |
| 24 | Gateway pods Ready=True | `kubectl get pods -o jsonpath` | Script check 2 | ✅ |
| 25 | Deployment replicas == spec.replicas | `kubectl get deployment` | Script check 2 | ✅ |
| 26 | Pod on n7 Running + Ready=True | Per-node check | Script check 2 | ✅ |
| 27 | Pod on n8 Running + Ready=True | Per-node check | Script check 2 | ✅ |
| **Liveness** | | | | |
| 28 | Liveness probe configured | `kubectl get deployment -o yaml \| grep livenessProbe` | manifests | ✅ |
| 29 | Startup probe configured | `kubectl get deployment -o yaml \| grep startupProbe` | manifests | ✅ |
| 30 | Readiness probe configured | `kubectl get deployment -o yaml \| grep readinessProbe` | manifests | ✅ |
| **Diagnostics** | | | | |
| 31 | Full diagnostic script passes | `bash scripts/check-gateway-32b.sh` → exit 0 | Script | ✅ |
| 32 | dnsPolicy acceptance gate test | `bash scripts/test-check-gateway-dns-policy.sh` → exit 0 | Script | ✅ |
| 33 | All 33 checks PASS | Script output | Script | ✅ |
| **Regression** | | | | |
| 34 | No bash syntax errors | `bash -n scripts/check-gateway-32b.sh` | Validation | ✅ |
| 35 | No git whitespace issues | `git diff --check` | Validation | ✅ |
| 36 | No temporary/backup files | `git status` | Audit | ✅ |
| 37 | No hardcoded secrets | Secret scanner | Scan | ✅ |
| 38 | Only ClusterFirst accepted | Negative tests (6 cases) | DNS test script | ✅ |
