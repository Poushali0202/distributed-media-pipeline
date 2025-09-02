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

## License
MIT


---

## New: Built-in Dashboard
Visit **http://localhost:8000/dashboard** for live job counts and recent activity.

## New: Kubernetes Manifests
See `deploy/k8s/*.yaml` and `docs/k8s.md` for cluster deployment, plus an HPA for worker scaling.
