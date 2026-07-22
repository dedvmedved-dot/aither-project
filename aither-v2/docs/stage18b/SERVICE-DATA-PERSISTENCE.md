# Stage 18B — Service Data Persistence

## Validation Method

A marker file was written to the identity PVC and verified to persist after pod deletion and recreation.

## Marker

| Field | Value |
|-------|-------|
| Marker | `stage18b-persistence-marker-1784738828` |
| Path | `/data/stage18b-marker.txt` |
| Service | aither-identity |
| PVC | `aither-identity-data` |
| PV | `pv-aither-identity-data` (Retain policy) |

## Procedure

1. Write marker to PVC: `echo 'stage18b-persistence-marker-1784738828' > /data/stage18b-marker.txt`
2. Verify marker content via `crictl exec`
3. Delete pod: `kubectl delete pod -l app=aither-identity`
4. Wait for new pod creation and readiness
5. Verify marker content in new pod via `crictl exec`

## Result

| Step | Outcome |
|------|---------|
| Marker created | ✅ `stage18b-persistence-marker-1784738828` |
| Pod deleted | ✅ identity-79cbf4c96d-2rkgq → identity-79cbf4c96d-c7r2h |
| New pod Running | ✅ 1/1 |
| Marker preserved after pod recovery | ✅ `stage18b-persistence-marker-1784738828` |
| PVC/PV binding unchanged | ✅ Both `Bound` |

## Conclusion

Persistent data survives pod recreation. PVC/PV binding (`Retain` reclaim policy) ensures data is preserved across pod lifecycle events.
