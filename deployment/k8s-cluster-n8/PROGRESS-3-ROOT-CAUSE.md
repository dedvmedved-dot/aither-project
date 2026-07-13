# Прогресс #3: Корневая причина найдена + вопрос

## Статус: 14 июля 2026, ~01:00 МСК

### 🔥 КЛЮЧЕВОЕ ОТКРЫТИЕ

**SIGTERM etcd (exit 0) и SIGKILL apiserver (exit 137) — следствие наших `systemctl restart kubelet`.**

Цепочка доказана логами containerd:

```
systemctl restart kubelet
  → kubelet: StopContainer для всех статических подов
  → containerd: "StopContainer for <etcd> with timeout 300 (s)"
  → etcd: SIGTERM → graceful shutdown → exit 0
  → containerd: "StopContainer for <apiserver> with timeout 30 (s)"
  → apiserver: SIGTERM → не успевает за 30s → SIGKILL → exit 137
```

**Доказательства:**
- `journalctl -u containerd`: все `StopContainer for etcd` совпадают по времени с `Stopping kubelet.service`
- За 6 часов kubelet перезапускался 4 раза: **все 4 — наши ручные** (18:02-18:07 debugging, 23:10-23:46 восстановление)
- etcd attempt #49: запущен 23:46:19 → получил SIGTERM 23:46:55 → ровно в момент `systemctl restart kubelet`

### ✅ Достигнуто

| Результат | Детали |
|---|---|
| K8s: 2 ноды Ready | n8 (cp) + n7 (worker), обе stable |
| etcd SIGTERM | Источник: ручной restart kubelet |
| apiserver SIGKILL | Источник: kubelet StopContainer (timeout 30s) |
| auditd | Правила на сигналы + манифесты активны |
| inotifywait | Мониторит /etc/kubernetes/manifests |
| vLLM | 14B (n8) + 32B (n7) — работают |
| etcd snapshot | /root/k8s-recovery/etcd-*.db |
| n7 join | Через ручной CSR (автоматический не работает) |

### ⚠️ Проблемы

| Проблема | Статус |
|---|---|
| CoreDNS CrashLoopBackOff (1/2) | Ждёт диагностики |
| kube-proxy Error на n8 | Периодически |
| NVIDIA driver пакет удалён apt | Драйвер в ядре жив |
| containerd 1.7.28 (n8) vs 2.2.1 (n7) | Отложено |
| kubeadm join (авто TLS bootstrap) | Не работает, CSR вручную |

---

## ❓ Вопрос специалистам (один)

**Является ли `systemctl restart kubelet` единственной причиной нестабильности, или есть скрытый источник падений apiserver?**

Мы рестартуем kubelet потому что видим, что apiserver упал. Но упал ли он САМ, или мы создали самоподдерживающийся цикл:

```
apiserver падает (причина X?)
  → мы видим connection refused
  → делаем systemctl restart kubelet
  → etcd получает SIGTERM
  → cascade failure
  → кластер восстанавливается
  → apiserver снова падает?
```

**Гипотеза:** если НЕ рестартовать kubelet, кластер стабилен. Apiserver падает только как следствие рестарта kubelet (apiserver не успевает graceful shutdown за 30 секунд при StopContainer).

**Вопрос:** так ли это? Может ли apiserver падать по другой причине, которую мы ещё не обнаружили?

---

## 📁 Файлы

- Snapshot etcd: `/root/k8s-recovery/etcd-*.db`
- Манифесты (backup): `/root/k8s-recovery/*.yaml.*`
- auditd: правила активны на n8
- inotifywait лог: `/tmp/inotify-manifests.log` (n8)
- Репозиторий: `aither-project/deployment/k8s-cluster-n8/`
