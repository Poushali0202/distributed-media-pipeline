# Runbook

## Common Checks
- Is Redis up? (`docker compose ps`, check `redis`)
- Is Worker connected? (Flower UI: http://localhost:5555)
- Are buckets created? (MinIO console: http://localhost:9001)
- API health: `GET /healthz`

## Symptoms & Remedies
- **Jobs stuck in PENDING**: Worker not connected; restart `worker` service.
- **Processing fails**: Check worker logs for ffmpeg/Pillow errors.
- **Artifacts missing**: Verify outputs bucket and DB records; re-run job—idempotent.
- **Slow processing**: Scale workers; consider smaller CRF/preset for ffmpeg.

## SLOs (demo)
- 95% jobs < 2 minutes for <100MB media.
