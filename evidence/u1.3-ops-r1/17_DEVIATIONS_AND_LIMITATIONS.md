# U1.3-OPS-R1 — DEVIATIONS AND LIMITATIONS

## Runtime Checks

| Check | Status | Reason |
|-------|:------:|--------|
| Shutdown execution | BLOCKED | No isolated environment or approved maintenance window |
| Production monitoring | DOCUMENTARY ONLY | Prometheus/Grafana described in docs; runtime presence not independently verified |
| Alertmanager | NOT VERIFIED | Documented but not tested in runtime |
| Database restore | NOT EXECUTED | Requires maintenance window |
| Secrets restore | NOT EXECUTED | Requires maintenance window |
| PV/PVC recovery | NOT EXECUTED | No PVCs in current deployment |
| Full DR | NOT EXECUTED | Beyond scope of operational readiness gate |
| Load test | NOT EXECUTED | Not requested in U1.3-OPS |
| Internet zone DNS reliability | TRANSIENT ISSUE | DNS resolution timeout observed during probe; recovered automatically |

## Documentation Coverage

| Area | Status |
|------|:------:|
| Operations procedures | ✅ COMPLETE |
| Deployment guide | ✅ COMPLETE |
| Rollback guide | ✅ COMPLETE |
| Backup/restore guide | ✅ COMPLETE (RPO/RTO/encryption → basic coverage) |
| Monitoring guide | ✅ COMPLETE |
| Troubleshooting guide | ✅ COMPLETE |
| User documentation | ✅ 17/17 scenarios |

## Known Limitations

1. **No isolated test environment** — shutdown test could not be performed without affecting production
2. **Prometheus/Grafana** — documented architecture but not independently verified as running
3. **Disaster recovery** — procedures documented but full DR drill not performed
4. **Internet Zone DNS** — transient resolution failures observed; root cause not investigated (likely VPS2 connectivity)
5. **RPO/RTO** — basic coverage in backup guide; formal SLA not defined
