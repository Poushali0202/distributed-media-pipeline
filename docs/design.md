# Design

## Goals
- Distributed, horizontally scalable processing of images & video.
- Simple, reproducible demo with Docker Compose.
- Clear API for uploads and job control, with presigned URLs.
- Idempotent processing and durable storage of artifacts.

## Components
- FastAPI for HTTP API (uploads, jobs).
- Celery (Redis broker) for task queueing.
- MinIO for object storage.
- Postgres for job & artifact metadata.
- Workers for processing: ffmpeg (video), Pillow (image).

## Idempotency
- Use `media_id` as a stable key; outputs named by operation and media_id.
- DB uses UPSERT semantics on artifacts to avoid duplicates.
- Retries are safe: re-uploads replace the same object key.

## Backpressure and Scaling
- Redis queue depth indicates load; scale worker replicas accordingly.
- Optional rate limiting per worker; future: DLQ and priority queues.

## Observability
- Flower UI for Celery status.
- (Stretch) Add Prometheus exporters, logs, and traces.

## Security
- Signed upload URLs (future).
- Bucket-level least-privilege (demo uses root keys).

## Future Extensions
- GPU worker for detection/segmentation.
- Vector embeddings + semantic search.
- K8s manifests + HPA on queue lag.
