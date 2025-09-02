# Distributed Image & Video Processing Pipeline (Celery + FastAPI + MinIO + ffmpeg)

**One-command demo** of a scalable media-processing pipeline. Upload media via API,
queue jobs, process on distributed workers (with `ffmpeg` for videos and Pillow for images),
and fetch outputs from S3-compatible storage (MinIO). Includes Flower for task monitoring.

> Great fit for SWE/SRE internship applications: shows distributed systems, reliability,
> observability, and practical ML/media processing hooks.

## Architecture

- **API**: FastAPI (upload media, create jobs, query status, presigned URLs)
- **Queue**: Celery on Redis
- **Workers**: Python Celery workers using `ffmpeg` (video) and `Pillow` (images)
- **Storage**: MinIO (S3 compatible) with buckets `media` and `outputs`
- **DB**: Postgres for jobs & artifacts
- **Monitoring**: Flower dashboard

```
[client] -> FastAPI -> Redis (Celery) -> Worker(s)
   |             |            |
   |             |            +-> MinIO (download/upload)
   |             +-> Postgres (job state, artifacts)
   +-> Query job status & get presigned URLs
```

## Quickstart

### Prereqs
- Docker & Docker Compose

### Run
```bash
# from repo root
docker compose up --build -d
# View logs
docker compose logs -f api worker
```

### Services
- API: http://localhost:8000/docs (Swagger)
- Flower (Celery monitoring): http://localhost:5555
- MinIO Console: http://localhost:9001 (user: `minio`, pass: `minio12345`)
- Postgres: localhost:5432 (user/pass/db: `media`/`media`/`media`)
- Redis: localhost:6379

> Buckets `media` and `outputs` are auto-created on startup.

### Scale workers
```bash
docker compose up -d --scale worker=3
```

## Try it

1) **Upload media**
```bash
curl -F "file=@sample_data/bunny.mp4" http://localhost:8000/media
# -> {"media_id": "...", "object_key": "media/<id>.mp4"}
```

2) **Create a processing job**
```bash
curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json"   -d '{"media_id":"<paste from step 1>","operations":["transcode_480p","thumbnail"]}'
# -> {"job_id":"..."}
```

3) **Check status**
```bash
curl http://localhost:8000/jobs/<job_id>
```

4) **List artifacts & get presigned URLs**
```bash
curl http://localhost:8000/media/<media_id>/artifacts
```

## Tech & Choices

- **Exactly-once-ish**: at-least-once Celery with idempotent DB writes and object keys
- **Backpressure**: let Redis queue grow; scale workers; add rate limiters/timeouts
- **Extensible**: add GPU worker, embeddings, CRDT status updates, retries/DLQ, Prometheus

## Resume bullets (suggested)

- Designed and deployed a Celery/Redis-based distributed media processing pipeline on Docker,
  processing concurrent jobs with ffmpeg and Pillow; tracked state in Postgres and stored
  artifacts in MinIO; exposed REST APIs and monitoring via Flower.
- Achieved horizontal scalability (N workers) and idempotent processing with content-hash keys;
  implemented thumbnail and 480p transcode with presigned URL retrieval.

## Repository layout

```
/docs
  design.md
  runbook.md
  benchmarks.md
/services
  common/...
  api/...
  worker/...
/deploy
  docker-compose.yml (root-level)
sample_data/
```

## License
MIT


---

## New: Built-in Dashboard
Visit **http://localhost:8000/dashboard** for live job counts and recent activity.

## New: Kubernetes Manifests
See `deploy/k8s/*.yaml` and `docs/k8s.md` for cluster deployment, plus an HPA for worker scaling.

## Optional GPU Worker (Stub)
- Folder: `services/worker-gpu/`
- Queue: `gpu`
- Demonstrates an embedding + GPU-ready worker structure (uses CPU torch by default).
- Uncomment the `worker-gpu` block in `docker-compose.yml` and configure GPUs to try it.
