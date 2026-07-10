# 02-deployment-guide.md — Пошаговое развёртывание (v1.2.0)

## Требования

- Astra Linux SE 1.8 (Смоленск) или Ubuntu 24.04
- 2 сервера с NVIDIA GPU (минимум 1× RTX 6000 каждый)
- K8s кластер (1 control-plane + 1 worker)
- Внешний диск 64+ GB для моделей
- PVC 20 GB для ChromaDB (на n7-gpu)

## Шаг 1: Подготовка ОС

```bash
# На всех узлах
apt-get update && apt-get install -y docker.io containerd nvidia-container-toolkit
systemctl enable --now docker containerd
```

## Шаг 2: NVIDIA + containerd

```bash
# Установка NVIDIA-драйвера (Astra Linux)
apt-get install -y nvidia-detect nvidia-driver-570
reboot

# После ребута
nvidia-smi  # должен показать GPU
```

## Шаг 3: Kubernetes

```bash
# Control-plane (n8)
kubeadm init --pod-network-cidr=10.244.0.0/16
kubectl apply -f https://github.com/flannel-io/flannel/releases/download/v0.25.7/kube-flannel.yml

# Worker (n7)
kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>
```

## Шаг 4: GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace
```

## Шаг 5: Модели

```bash
# Скопировать модели на оба узла в /mnt/models/
ls /mnt/models/Qwen2.5-14B-Instruct/
ls /mnt/models/Qwen2.5-32B-Instruct-GPTQ/
```

## Шаг 6: Платформа Aither

```bash
cd offline-deploy/
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/
kubectl apply -f k8s/chromadb/        # ChromaDB 0.5.23 + PVC + chroma-proxy
kubectl apply -f k8s/vllm-14b/
kubectl apply -f k8s/vllm-32b/
kubectl apply -f k8s/gateway/
kubectl apply -f k8s/monitoring/

# Проверка
kubectl get pods -w
```

### Проверка RAG после деплоя

```bash
# chroma-proxy должен быть Running
kubectl get pods -l app=chroma-proxy

# Инжест учебника в ChromaDB
kubectl exec deploy/chroma-proxy -- python3 /chroma/ingest_textbook.py

# Проверка статуса
curl http://chroma-proxy.default.svc.cluster.local:9000/status
# → {"collection":"textbook","documents":322,"embed_dim":384,"status":"ok"}
```

## Шаг 7: Портал (VPS2)

```bash
cd /root/aither-project/portal
cp ../offline-deploy/configs/bff/.env.template .env
# Заполнить .env (JWT_SECRET, OAuth ключи, CORE_API)
npm install
npm start
```

## Шаг 8: Nginx

```bash
cp offline-deploy/configs/nginx/nginx.conf /etc/nginx/sites-enabled/aither
nginx -t && systemctl reload nginx
```

## Шаг 9: Проверка

```bash
make test
```

Все тесты должны пройти.
