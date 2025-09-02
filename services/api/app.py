import json
import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from common.config import settings
from common.db import Base, engine, SessionLocal
from common.models import Job, Artifact, JobStatus
from common.storage import get_minio, generate_media_id, object_key_for_media

from celery import Celery

app = FastAPI(title="Distributed Media Pipeline API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# init DB
Base.metadata.create_all(bind=engine)

# Celery app
celery_app = Celery("media_pipeline", broker=settings.redis_url, backend=settings.redis_url)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from datetime import timedelta

# Mount the dashboard (static files)
app.mount("/dashboard", StaticFiles(directory="static/dashboard", html=True), name="dashboard")

class JobListItem(BaseModel):
    id: str
    media_id: str
    status: str
    created_at: str
    updated_at: str

@app.get("/jobs", response_model=list[JobListItem])
def list_jobs(limit: int = 50):
    with SessionLocal() as db:
        rows = db.execute(select(Job).order_by(Job.created_at.desc()).limit(limit)).scalars().all()
        return [
            {
                "id": str(row.id),
                "media_id": row.media_id,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "updated_at": (row.updated_at.isoformat() if row.updated_at else None),
            } for row in rows
        ]

class StatsResp(BaseModel):
    counts: dict
    p50_latency_s: float | None
    p95_latency_s: float | None

@app.get("/stats", response_model=StatsResp)
def stats():
    with SessionLocal() as db:
        # Counts by status
        counts = {s.value: 0 for s in JobStatus}
        rows = db.execute(select(Job.status, func.count()).group_by(Job.status)).all()
        for status, c in rows:
            counts[status.value] = c

        # Compute durations for completed jobs
        done_rows = db.execute(select(Job.created_at, Job.updated_at).where(Job.status == JobStatus.done)).all()
        durations = []
        for created_at, updated_at in done_rows:
            if created_at and updated_at:
                durations.append((updated_at - created_at).total_seconds())
        durations.sort()
        def percentile(values, p):
            if not values: return None
            k = (len(values)-1) * (p/100.0)
            f = int(k); c = min(f+1, len(values)-1); d = k - f
            return values[f] + (values[c]-values[f]) * d if c>f else values[f]
        p50 = percentile(durations, 50) if durations else None
        p95 = percentile(durations, 95) if durations else None
        return {"counts": counts, "p50_latency_s": p50, "p95_latency_s": p95}


class UploadResp(BaseModel):
    media_id: str
    object_key: str

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/media", response_model=UploadResp)
async def upload_media(file: UploadFile = File(...)):
    try:
        media_id = generate_media_id()
        object_key = f"{settings.media_bucket}/{object_key_for_media(media_id, file.filename)}"
        client = get_minio()
        data = await file.read()
        client.put_object(
            settings.media_bucket,
            object_key.split("/",1)[1],
            data=io.BytesIO(data),
            length=len(data),
            content_type=file.content_type or "application/octet-stream",
        )
        return {"media_id": media_id, "object_key": object_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class JobReq(BaseModel):
    media_id: str
    operations: List[str] = ["transcode_480p", "thumbnail"]

class JobResp(BaseModel):
    job_id: str

@app.post("/jobs", response_model=JobResp)
def create_job(req: JobReq):
    with SessionLocal() as db:
        try:
            job = Job(media_id=req.media_id, operations=json.dumps(req.operations), status=JobStatus.queued)
            db.add(job)
            db.commit()
            db.refresh(job)
            # enqueue celery task
            celery_app.send_task("worker.tasks.process_job", args=[str(job.id)])
            return {"job_id": str(job.id)}
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

class JobStatusResp(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None

@app.get("/jobs/{job_id}", response_model=JobStatusResp)
def get_job(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, uuid.UUID(job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"job_id": job_id, "status": job.status, "error": job.error}

class ArtifactItem(BaseModel):
    id: str
    kind: str
    object_key: str
    size_bytes: Optional[int]
    url: Optional[str]

@app.get("/media/{media_id}/artifacts", response_model=list[ArtifactItem])
def list_artifacts(media_id: str):
    from datetime import timedelta
    client = get_minio()
    with SessionLocal() as db:
        q = db.execute(select(Artifact).where(Artifact.media_id == media_id)).scalars().all()
        items = []
        for a in q:
            # presigned URL
            bucket, key = a.object_key.split("/",1)
            url = client.presigned_get_object(bucket, key, expires=timedelta(hours=1))
	    public_base = os.getenv("PUBLIC_MINIO_BASE", "http://localhost:9000")
	    url = url.replace("http://minio:9000", public_base)
	    items.append({
    		"id": str(a.id),
    		"kind": a.kind,
    		"object_key": a.object_key,
    		"size_bytes": a.size_bytes,
    		"url": url
	    })

# Fix: import io used above
import io  # placed here after FastAPI definition to avoid circular lints
