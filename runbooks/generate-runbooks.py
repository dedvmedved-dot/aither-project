#!/usr/bin/env python3
"""Генератор 100 runbook-скриптов: 50 Aither + 50 Брест."""

import os

AITHER_DIR = "/opt/aiops-aither/runbooks/aither"
BREST_DIR = "/opt/aiops-aither/runbooks/brest"

AITHER_RUNBOOKS = [
    # K1 — Сетевые (10)
    ("rb-aither-k1-01-loss-n7.sh", "n7 packet loss 10%", "ssh n7 'tc qdisc add dev ens1f0 root netem loss 10%'", "ssh n7 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-02-loss-n8.sh", "n8 packet loss 15%", "ssh n8 'tc qdisc add dev ens1f0 root netem loss 15%'", "ssh n8 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-03-delay-n7.sh", "n7 latency 200ms", "ssh n7 'tc qdisc add dev ens1f0 root netem delay 200ms 50ms'", "ssh n7 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-04-delay-n8.sh", "n8 latency 500ms", "ssh n8 'tc qdisc add dev ens1f0 root netem delay 500ms 100ms'", "ssh n8 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-05-jitter-n7n8.sh", "n7→n8 jitter 50ms", "ssh n7 'tc qdisc add dev ens1f0 root netem delay 50ms 50ms 25%'", "ssh n7 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-06-bandwidth-n7.sh", "n7 bandwidth 1Mbps", "ssh n7 'tc qdisc add dev ens1f0 root tbf rate 1mbit burst 32kbit latency 400ms'", "ssh n7 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-07-drop-n7n8.sh", "iptables DROP n7↔n8", "ssh n8 'iptables -A INPUT -s 10.129.13.77 -j DROP'", "ssh n8 'iptables -D INPUT -s 10.129.13.77 -j DROP'"),
    ("rb-aither-k1-08-drop-vps2.sh", "iptables DROP n8→VPS2", "ssh n8 'iptables -A OUTPUT -d 170.168.91.95 -j DROP'", "ssh n8 'iptables -D OUTPUT -d 170.168.91.95 -j DROP'"),
    ("rb-aither-k1-09-corrupt-n7.sh", "n7 packet corruption 5%", "ssh n7 'tc qdisc add dev ens1f0 root netem corrupt 5%'", "ssh n7 'tc qdisc del dev ens1f0 root'"),
    ("rb-aither-k1-10-duplicate-n7.sh", "n7 packet duplicate 10%", "ssh n7 'tc qdisc add dev ens1f0 root netem duplicate 10%'", "ssh n7 'tc qdisc del dev ens1f0 root'"),

    # K2 — Вычислительные (8)
    ("rb-aither-k2-01-cpu-stress-n8.sh", "n8 CPU stress 4 ядра", "ssh n8 'stress-ng --cpu 4 --timeout 180s &'", "ssh n8 'pkill -f stress-ng'"),
    ("rb-aither-k2-02-cpu-stress-n7.sh", "n7 CPU stress 8 ядер", "ssh n7 'stress-ng --cpu 8 --timeout 180s &'", "ssh n7 'pkill -f stress-ng'"),
    ("rb-aither-k2-03-gpu-mem-n7.sh", "n7 GPU memory exhaustion", "ssh n7 'python3 -c \"import torch; [torch.zeros(512,512,512,dtype=torch.float16,device=\\\"cuda:0\\\") for _ in range(4)]; import time; time.sleep(120)\" &'", "ssh n7 'pkill -f torch.zeros'"),
    ("rb-aither-k2-04-gpu-compute-n7.sh", "n7 GPU compute stress", "ssh n7 'python3 -c \"import torch; a=torch.randn(4096,4096,device=\\\"cuda:0\\\"); [a@a for _ in range(200)]\" &'", "ssh n7 'pkill -f cuda:0'"),
    ("rb-aither-k2-05-gpu-temp-n7.sh", "n7 GPU thermal throttle", "ssh n7 'nvidia-smi -pm 1; nvidia-smi -pl 100'", "ssh n7 'nvidia-smi -pl 250'"),
    ("rb-aither-k2-06-io-stress-n8.sh", "n8 I/O stress", "ssh n8 'stress-ng --io 4 --timeout 180s &'", "ssh n8 'pkill -f stress-ng.*io'"),
    ("rb-aither-k2-07-hdd-stress-n8.sh", "n8 HDD stress", "ssh n8 'stress-ng --hdd 2 --timeout 180s &'", "ssh n8 'pkill -f stress-ng.*hdd'"),
    ("rb-aither-k2-08-vm-stress-n7.sh", "n7 VM stress", "ssh n7 'stress-ng --vm 4 --vm-bytes 2G --timeout 180s &'", "ssh n7 'pkill -f stress-ng.*vm'"),

    # K3 — Память (5)
    ("rb-aither-k3-01-oom-n8.sh", "n8 OOM killer", "ssh n8 'stress-ng --vm 4 --vm-bytes 95% --timeout 60s &'", "ssh n8 'pkill -f stress-ng.*vm'"),
    ("rb-aither-k3-02-oom-n7.sh", "n7 OOM killer", "ssh n7 'stress-ng --vm 8 --vm-bytes 95% --timeout 60s &'", "ssh n7 'pkill -f stress-ng.*vm'"),
    ("rb-aither-k3-03-swap-n8.sh", "n8 swap exhaustion", "ssh n8 'stress-ng --vm 2 --vm-bytes 110% --timeout 60s &'", "ssh n8 'pkill -f stress-ng.*vm'"),
    ("rb-aither-k3-04-mlock-n8.sh", "n8 memory lock", "ssh n8 'stress-ng --mlock 2 --timeout 120s &'", "ssh n8 'pkill -f stress-ng.*mlock'"),
    ("rb-aither-k3-05-brk-n7.sh", "n7 brk() exhaustion", "ssh n7 'stress-ng --brk 4 --timeout 120s &'", "ssh n7 'pkill -f stress-ng.*brk'"),

    # K4 — Дисковые (5)
    ("rb-aither-k4-01-fio-n8.sh", "n8 fio random write", "ssh n8 'fio --name=rw --ioengine=libaio --iodepth=16 --rw=randwrite --bs=4k --size=2G --time_based --runtime=120 --filename=/tmp/fio-test &'", "rm -f /tmp/fio-test ; ssh n8 'rm -f /tmp/fio-test'"),
    ("rb-aither-k4-02-inodes-n8.sh", "n8 inode exhaustion", "ssh n8 'for i in $(seq 1 50000); do touch /tmp/inodes/$i 2>/dev/null; done'", "ssh n8 'rm -rf /tmp/inodes'"),
    ("rb-aither-k4-03-ro-fs-n8.sh", "n8 read-only FS", "ssh n8 'mount -o remount,ro /tmp 2>/dev/null || true'", "ssh n8 'mount -o remount,rw /tmp 2>/dev/null || true'"),
    ("rb-aither-k4-04-fio-n7.sh", "n7 fio random read", "ssh n7 'fio --name=rr --ioengine=libaio --iodepth=16 --rw=randread --bs=4k --size=2G --time_based --runtime=120 --filename=/tmp/fio-test &'", "rm -f /tmp/fio-test ; ssh n7 'rm -f /tmp/fio-test'"),
    ("rb-aither-k4-05-disk-full-n8.sh", "n8 disk full (dd)", "ssh n8 'dd if=/dev/zero of=/tmp/fill bs=1M count=2000 2>/dev/null'", "ssh n8 'rm -f /tmp/fill'"),

    # K5 — Сервисные (10)
    ("rb-aither-k5-01-restart-pg.sh", "PostgreSQL restart", "ssh n8 'systemctl stop postgresql'", "ssh n8 'systemctl start postgresql'"),
    ("rb-aither-k5-02-restart-redis.sh", "Redis restart", "ssh n8 'systemctl stop redis'", "ssh n8 'systemctl start redis'"),
    ("rb-aither-k5-03-restart-gateway.sh", "Gateway restart", "ssh n8 'systemctl restart aither-gateway'", "ssh n8 'systemctl start aither-gateway'"),
    ("rb-aither-k5-04-restart-vllm32b.sh", "vLLM 32B restart", "ssh n7 'systemctl restart vllm-32b'", "ssh n7 'systemctl start vllm-32b'"),
    ("rb-aither-k5-05-restart-vllm14b.sh", "vLLM 14B pod restart", "ssh n8 'kubectl delete pod -l app=vllm-14b'", "ssh n8 'kubectl wait --for=condition=ready pod -l app=vllm-14b --timeout=300s'"),
    ("rb-aither-k5-06-kill-pg.sh", "kill -9 PostgreSQL", "ssh n8 'kill -9 $(pgrep -f postgres)'", "ssh n8 'systemctl start postgresql'"),
    ("rb-aither-k5-07-kill-gateway.sh", "kill -9 Gateway", "ssh n8 'kill -9 $(pgrep -f gateway.py)'", "ssh n8 'systemctl start aither-gateway'"),
    ("rb-aither-k5-08-kill-vllm.sh", "kill -9 vLLM", "ssh n7 'kill -9 $(pgrep -f vllm)'", "ssh n7 'systemctl start vllm-32b'"),
    ("rb-aither-k5-09-drain-node-n7.sh", "K8s drain n7", "ssh n8 'kubectl drain bootsman-k8s-clnt01-n7-gpu --ignore-daemonsets --delete-emptydir-data'", "ssh n8 'kubectl uncordon bootsman-k8s-clnt01-n7-gpu'"),
    ("rb-aither-k5-10-cordon-node-n8.sh", "K8s cordon n8", "ssh n8 'kubectl cordon bootsman-k8s-clnt01-n8-gpu'", "ssh n8 'kubectl uncordon bootsman-k8s-clnt01-n8-gpu'"),

    # K6 — Каскадные (5)
    ("rb-aither-k6-01-pg-redis.sh", "PG + Redis simultaneous stop", "ssh n8 'systemctl stop postgresql; systemctl stop redis'", "ssh n8 'systemctl start postgresql; systemctl start redis'"),
    ("rb-aither-k6-02-gateway-redis.sh", "Gateway + Redis failure", "ssh n8 'systemctl stop redis; sleep 2; systemctl stop aither-gateway'", "ssh n8 'systemctl start redis; sleep 2; systemctl start aither-gateway'"),
    ("rb-aither-k6-03-vllm-gateway.sh", "vLLM + Gateway cascade", "ssh n7 'systemctl stop vllm-32b'; ssh n8 'systemctl stop aither-gateway'", "ssh n7 'systemctl start vllm-32b'; ssh n8 'systemctl start aither-gateway'"),
    ("rb-aither-k6-04-all-services.sh", "All services stop", "ssh n8 'systemctl stop postgresql redis aither-gateway'; ssh n7 'systemctl stop vllm-32b'", "ssh n7 'systemctl start vllm-32b'; ssh n8 'systemctl start postgresql redis aither-gateway'"),
    ("rb-aither-k6-05-k8s-control.sh", "K8s control plane failure", "ssh n8 'systemctl stop kubelet'", "ssh n8 'systemctl start kubelet'"),

    # K7 — Безопасность (5)
    ("rb-aither-k7-01-iptables-api.sh", "Block external API port", "ssh n8 'iptables -A INPUT -p tcp --dport 8080 -j DROP'", "ssh n8 'iptables -D INPUT -p tcp --dport 8080 -j DROP'"),
    ("rb-aither-k7-02-iptables-pg.sh", "Block PostgreSQL port", "ssh n8 'iptables -A INPUT -p tcp --dport 5432 -j DROP'", "ssh n8 'iptables -D INPUT -p tcp --dport 5432 -j DROP'"),
    ("rb-aither-k7-03-iptables-redis.sh", "Block Redis port", "ssh n8 'iptables -A INPUT -p tcp --dport 6379 -j DROP'", "ssh n8 'iptables -D INPUT -p tcp --dport 6379 -j DROP'"),
    ("rb-aither-k7-04-vault-lock.sh", "Vault seal", "ssh n8 'vault operator seal 2>/dev/null || echo vault-sealed'", "ssh n8 'vault operator unseal 2>/dev/null || echo vault-unseal-skip'"),
    ("rb-aither-k7-05-rate-limit.sh", "Rate limit spike (100 req/s)", "for i in $(seq 1 100); do curl -s -o /dev/null http://localhost:8080/health & done", "sleep 60"),

    # K8 — Специфические (2)
    ("rb-aither-k8-01-gpu-ecc.sh", "GPU ECC error injection", "ssh n7 'nvidia-smi -e 1 2>/dev/null || echo ECC-already-enabled'", "ssh n7 'nvidia-smi -e 0 2>/dev/null || echo ECC-reset'"),
    ("rb-aither-k8-02-nvidia-fallback.sh", "NVIDIA driver reload", "ssh n7 'modprobe -r nvidia_uvm nvidia_drm nvidia_modeset nvidia 2>/dev/null || true'", "ssh n7 'modprobe nvidia nvidia_modeset nvidia_drm nvidia_uvm'"),
]

BREST_RUNBOOKS = [
    # K1 — Сетевые Брест (10)
    ("rb-brest-k1-01-loss.sh", "Брест loss 10%", "ssh brest-gw 'tc qdisc add dev eth0 root netem loss 10%'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),
    ("rb-brest-k1-02-delay.sh", "Брест latency 300ms", "ssh brest-gw 'tc qdisc add dev eth0 root netem delay 300ms 50ms'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),
    ("rb-brest-k1-03-bandwidth.sh", "Брест bandwidth 2Mbps", "ssh brest-gw 'tc qdisc add dev eth0 root tbf rate 2mbit burst 32kbit latency 400ms'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),
    ("rb-brest-k1-04-vpn-drop.sh", "VPN Cisco DROP", "ssh brest-gw 'iptables -A INPUT -i tun0 -j DROP'", "ssh brest-gw 'iptables -D INPUT -i tun0 -j DROP'"),
    ("rb-brest-k1-05-vlan-drop.sh", "VLAN 308 isolation", "ssh mikrotik '/ip firewall filter add chain=forward src-address=10.129.13.0/24 action=drop'", "ssh mikrotik '/ip firewall filter remove [find comment=test-drop]'"),
    ("rb-brest-k1-06-dns-fail.sh", "DNS failure", "cp /etc/resolv.conf /etc/resolv.conf.bak; echo > /etc/resolv.conf", "cp /etc/resolv.conf.bak /etc/resolv.conf"),
    ("rb-brest-k1-07-jitter.sh", "Брест jitter 100ms", "ssh brest-gw 'tc qdisc add dev eth0 root netem delay 50ms 100ms 50%'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),
    ("rb-brest-k1-08-corrupt.sh", "Брест corruption 3%", "ssh brest-gw 'tc qdisc add dev eth0 root netem corrupt 3%'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),
    ("rb-brest-k1-09-reorder.sh", "Брест reorder 25%", "ssh brest-gw 'tc qdisc add dev eth0 root netem delay 10ms reorder 25% 50%'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),
    ("rb-brest-k1-10-rate.sh", "Брест rate limit 5Mbps", "ssh brest-gw 'tc qdisc add dev eth0 root tbf rate 5mbit burst 64kbit latency 200ms'", "ssh brest-gw 'tc qdisc del dev eth0 root'"),

    # K2 — Вычислительные Брест (8)
    ("rb-brest-k2-01-cpu.sh", "Брест CPU 4 ядра", "ssh brest-node 'stress-ng --cpu 4 --timeout 180s &'", "ssh brest-node 'pkill -f stress-ng'"),
    ("rb-brest-k2-02-cpu-all.sh", "Брест CPU 16 ядер", "ssh brest-node 'stress-ng --cpu 16 --timeout 180s &'", "ssh brest-node 'pkill -f stress-ng'"),
    ("rb-brest-k2-03-matrix.sh", "Брест matrix stress", "ssh brest-node 'stress-ng --matrix 4 --timeout 180s &'", "ssh brest-node 'pkill -f stress-ng.*matrix'"),
    ("rb-brest-k2-04-crypto.sh", "Брест crypto stress", "ssh brest-node 'stress-ng --crypt 4 --timeout 120s &'", "ssh brest-node 'pkill -f stress-ng.*crypt'"),
    ("rb-brest-k2-05-fork.sh", "Брест fork bomb", "ssh brest-node 'stress-ng --fork 100 --timeout 30s &'", "ssh brest-node 'pkill -f stress-ng.*fork'"),
    ("rb-brest-k2-06-context.sh", "Брест context switch", "ssh brest-node 'stress-ng --context 8 --timeout 180s &'", "ssh brest-node 'pkill -f stress-ng.*context'"),
    ("rb-brest-k2-07-vecmath.sh", "Брест FPU stress", "ssh brest-node 'stress-ng --vecmath 4 --timeout 120s &'", "ssh brest-node 'pkill -f stress-ng.*vecmath'"),
    ("rb-brest-k2-08-sigfpe.sh", "Брест FP exception flood", "ssh brest-node 'stress-ng --sigfpe 4 --timeout 60s &'", "ssh brest-node 'pkill -f stress-ng.*sigfpe'"),

    # K3 — Память Брест (5)
    ("rb-brest-k3-01-oom.sh", "Брест OOM killer", "ssh brest-node 'stress-ng --vm 4 --vm-bytes 95% --timeout 60s &'", "ssh brest-node 'pkill -f stress-ng.*vm'"),
    ("rb-brest-k3-02-swap.sh", "Брест swap exhaustion", "ssh brest-node 'stress-ng --vm 2 --vm-bytes 110% --timeout 60s &'", "ssh brest-node 'pkill -f stress-ng.*vm'"),
    ("rb-brest-k3-03-stack.sh", "Брест stack overflow", "ssh brest-node 'stress-ng --stack 4 --timeout 60s &'", "ssh brest-node 'pkill -f stress-ng.*stack'"),
    ("rb-brest-k3-04-bigheap.sh", "Брест big heap", "ssh brest-node 'stress-ng --bigheap 2 --timeout 60s &'", "ssh brest-node 'pkill -f stress-ng.*bigheap'"),
    ("rb-brest-k3-05-shm.sh", "Брест shared memory", "ssh brest-node 'stress-ng --shm 4 --timeout 120s &'", "ssh brest-node 'pkill -f stress-ng.*shm'"),

    # K4 — Ceph + DRBD (10)
    ("rb-brest-k4-01-ceph-osd-down.sh", "Ceph OSD down", "ssh brest-ceph 'systemctl stop ceph-osd@0'", "ssh brest-ceph 'systemctl start ceph-osd@0'"),
    ("rb-brest-k4-02-ceph-mon-down.sh", "Ceph MON down", "ssh brest-ceph 'systemctl stop ceph-mon@brest'", "ssh brest-ceph 'systemctl start ceph-mon@brest'"),
    ("rb-brest-k4-03-ceph-pg-degraded.sh", "Ceph PG degraded", "ssh brest-ceph 'ceph osd out 0'", "ssh brest-ceph 'ceph osd in 0'"),
    ("rb-brest-k4-04-drbd-disconnect.sh", "DRBD disconnect", "ssh brest-node 'drbdadm disconnect r0'", "ssh brest-node 'drbdadm connect r0'"),
    ("rb-brest-k4-05-drbd-split-brain.sh", "DRBD split-brain", "ssh brest-node 'drbdadm secondary r0'", "ssh brest-node 'drbdadm primary r0'"),
    ("rb-brest-k4-06-drbd-resync.sh", "DRBD resync trigger", "ssh brest-node 'drbdadm invalidate r0'", "ssh brest-node 'drbdadm connect r0'"),
    ("rb-brest-k4-07-ceph-io.sh", "Ceph I/O stress", "ssh brest-ceph 'rados bench -p rbd 60 write &'", "ssh brest-ceph 'pkill -f rados'"),
    ("rb-brest-k4-08-fio-rbd.sh", "RBD fio stress", "ssh brest-node 'fio --name=test --ioengine=rbd --pool=rbd --rbdname=test --rw=randwrite --bs=4k --runtime=60 &'", "ssh brest-node 'pkill -f fio'"),
    ("rb-brest-k4-09-disk-full.sh", "Ceph disk full", "ssh brest-ceph 'dd if=/dev/zero of=/var/lib/ceph/osd/fill bs=1M count=5000 2>/dev/null'", "ssh brest-ceph 'rm -f /var/lib/ceph/osd/fill'"),
    ("rb-brest-k4-10-inode-ceph.sh", "Ceph FS inode exhaustion", "ssh brest-node 'for i in $(seq 1 50000); do touch /mnt/cephfs/inodes/$i 2>/dev/null; done'", "ssh brest-node 'rm -rf /mnt/cephfs/inodes/*'"),

    # K5 — Сервисы Брест (10)
    ("rb-brest-k5-01-freeipa-stop.sh", "FreeIPA stop", "ssh brest-ipa 'systemctl stop ipa'", "ssh brest-ipa 'systemctl start ipa'"),
    ("rb-brest-k5-02-httpd-stop.sh", "HTTPd stop", "ssh brest-ipa 'systemctl stop httpd'", "ssh brest-ipa 'systemctl start httpd'"),
    ("rb-brest-k5-03-ntpd-stop.sh", "NTPd stop", "ssh brest-ntp 'systemctl stop ntpd'", "ssh brest-ntp 'systemctl start ntpd'"),
    ("rb-brest-k5-04-ssh-kill.sh", "SSHd kill", "ssh brest-node 'kill -9 $(pgrep sshd)'", "ssh brest-node 'systemctl start sshd'"),
    ("rb-brest-k5-05-parsec-kill.sh", "Parsec kill", "ssh brest-node 'kill -9 $(pgrep parsec)'", "ssh brest-node 'systemctl start parsec'"),
    ("rb-brest-k5-06-chrony-stop.sh", "Chrony stop", "ssh brest-node 'systemctl stop chronyd'", "ssh brest-node 'systemctl start chronyd'"),
    ("rb-brest-k5-07-auditd-stop.sh", "Auditd stop", "ssh brest-node 'systemctl stop auditd'", "ssh brest-node 'systemctl start auditd'"),
    ("rb-brest-k5-08-firewalld-stop.sh", "Firewalld stop", "ssh brest-node 'systemctl stop firewalld'", "ssh brest-node 'systemctl start firewalld'"),
    ("rb-brest-k5-09-crond-kill.sh", "Crond kill", "ssh brest-node 'kill -9 $(pgrep crond)'", "ssh brest-node 'systemctl start crond'"),
    ("rb-brest-k5-10-syslog-kill.sh", "Syslog kill", "ssh brest-node 'kill -9 $(pgrep rsyslogd)'", "ssh brest-node 'systemctl start rsyslog'"),

    # K7 — Безопасность Брест (5)
    ("rb-brest-k7-01-parsec-block.sh", "Parsec mandatory block", "ssh brest-node 'setenforce 1'", "ssh brest-node 'setenforce 0'"),
    ("rb-brest-k7-02-selinux-enforce.sh", "SELinux enforce", "ssh brest-node 'setenforce 1'", "ssh brest-node 'setenforce 0'"),
    ("rb-brest-k7-03-iptables-audit.sh", "Audit rules flush", "ssh brest-node 'auditctl -D'", "ssh brest-node 'augenrules --load'"),
    ("rb-brest-k7-04-pam-lock.sh", "PAM lockout", "ssh brest-node 'pam_tally2 --user test --reset 2>/dev/null || true'", "ssh brest-node 'pam_tally2 --user test --reset 2>/dev/null || true'"),
    ("rb-brest-k7-05-umask-007.sh", "UMASK 0077", "echo 'umask 0077' > /tmp/umask-test", "rm /tmp/umask-test"),

    # K8 — Платформенные (2)
    ("rb-brest-k8-01-astra-lock.sh", "Astra Linux mandatory lock", "ssh brest-node 'astra-modeset 1 2>/dev/null || true'", "ssh brest-node 'astra-modeset 0 2>/dev/null || true'"),
    ("rb-brest-k8-02-mc-kill.sh", "MC kill", "ssh brest-node 'kill -9 $(pgrep mc)'", ""),
]


TEMPLATE = """#!/bin/bash
# {runbook_id} — {description}
# Часть ПМИ AIOps — испытания Aither + ПК СВ Брест
# Сгенерирован: {timestamp}

set -e
LOG="/opt/aiops-aither/logs/runbooks/{runbook_id}.log"
SSH_KEY="/root/.ssh/id_ed25519_n7n8"

log() {{
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"
}}

log "=== START {runbook_id} ==="
log "Description: {description}"

# Пре-проверка
log "Pre-check: health status"
curl -s --max-time 5 http://10.129.13.78:8080/health 2>/dev/null || echo "Gateway pre-check: UNREACHABLE"

# Инжекция
log "Injecting fault..."
{inject}

sleep 2

# Диагностика
log "Diagnostics after injection..."
curl -s --max-time 5 http://10.129.13.78:8080/health 2>/dev/null || echo "Gateway: DOWN"
curl -s --max-time 5 http://10.129.13.77:8000/health 2>/dev/null || echo "vLLM 32B: DOWN"
ssh -i $SSH_KEY -o ConnectTimeout=5 root@10.129.13.78 'pg_isready -U aither' 2>/dev/null || echo "PostgreSQL: DOWN"
ssh -i $SSH_KEY -o ConnectTimeout=5 root@10.129.13.78 'redis-cli ping' 2>/dev/null || echo "Redis: DOWN"

# Восстановление
log "Recovering..."
{recover}

sleep 2

# Пост-проверка
log "Post-check..."
curl -s --max-time 10 http://10.129.13.78:8080/health 2>/dev/null && log "Gateway: RECOVERED" || log "Gateway: STILL DOWN"

log "=== END {runbook_id} ==="
"""

from datetime import datetime

os.makedirs(AITHER_DIR, exist_ok=True)
os.makedirs(BREST_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S MSK")

count = 0
for target_dir, runbooks in [(AITHER_DIR, AITHER_RUNBOOKS), (BREST_DIR, BREST_RUNBOOKS)]:
    for filename, description, inject, recover in runbooks:
        path = os.path.join(target_dir, filename)
        content = TEMPLATE.format(
            runbook_id=filename.replace(".sh", ""),
            description=description,
            timestamp=timestamp,
            inject=inject,
            recover=recover,
        )
        with open(path, 'w') as f:
            f.write(content)
        os.chmod(path, 0o755)
        count += 1

print(f"Сгенерировано {count} runbook-скриптов")
print(f"  {AITHER_DIR}: {len(AITHER_RUNBOOKS)} скриптов")
print(f"  {BREST_DIR}: {len(BREST_RUNBOOKS)} скриптов")
