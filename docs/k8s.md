# Kubernetes Deployment

## Build & Push Images
Replace image names in manifests with your registry:
- `ghcr.io/<you>/media-api:latest`
- `ghcr.io/<you>/media-worker:latest`

```bash
docker build -t ghcr.io/<you>/media-api:latest services/api
docker build -t ghcr.io/<you>/media-worker:latest services/worker
docker push ghcr.io/<you>/media-api:latest
docker push ghcr.io/<you>/media-worker:latest
```

## Apply Manifests
```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/redis.yaml
kubectl apply -f deploy/k8s/postgres.yaml
kubectl apply -f deploy/k8s/minio.yaml
kubectl apply -f deploy/k8s/api.yaml
kubectl apply -f deploy/k8s/worker.yaml
kubectl apply -f deploy/k8s/flower.yaml
# (optional) kubectl apply -f deploy/k8s/ingress-example.yaml
```

## Scaling
The included HPA scales workers based on CPU utilization (60%). For **queue-length-based scaling**,
consider **KEDA** with the Redis scaler to target Celery queue depth.

## GPU Workers
- Build the optional `services/worker-gpu` and deploy a separate `Deployment` that listens on the `gpu` queue.
- For true GPU acceleration, base on an NVIDIA CUDA image and run with `--gpus all` (Docker) or set `nvidia.com/gpu` resource requests (K8s).
