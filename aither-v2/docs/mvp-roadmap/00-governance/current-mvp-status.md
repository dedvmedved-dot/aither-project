# Current MVP Status

Date: 2026-07-19

## Summary

| Area | Status | Evidence |
|---|---|---|
| Cluster/GPU | PASSED WITH FINDINGS | docs/mvp-roadmap/01-cluster-gpu/cluster-topology-report.md |
| GPU runtime | PASSED | docs/mvp-roadmap/01-cluster-gpu/gpu-runtime-validation.md |
| vLLM 14B | OBSERVED | |
| vLLM 32B | OBSERVED | |
| Gateway | PARTIAL | GW-01: 2/3 replicas ImagePullBackOff (stage 04) |
| Benchmark | OBSERVED | |
| TP=2 | HYPOTHESIZED | |
| BFF | NOT STARTED | |
| Redis RL | NOT STARTED | |
| Portal | NOT STARTED | |
| Monitoring | PARTIAL | |
| Provenance | NOT STARTED | |
| VPN | DIAGNOSED | |

## Current accepted topology

n7 = GPU worker (inference): vllm-14b-instruct, vllm-32b-gptq  
n8 = Control-plane + benchmark: kube-apiserver, etcd, scheduler, controller-manager, nginx-gateway-32b, benchmark-inference

## Current blockers

1. VPN/MTU instability (MTU ~1362, packet loss)
2. No HA (single GPU node n7)
3. No monitoring stack (Prometheus/Grafana)
4. Model provenance not documented
5. GW-01: Gateway replicas stuck in ImagePullBackOff (stage 04)

## Next approved stage

Stage: 01-cluster-gpu  
Status: PASSED WITH FINDINGS
