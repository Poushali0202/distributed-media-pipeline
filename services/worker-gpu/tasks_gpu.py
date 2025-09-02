import os, io, json, uuid, shutil, tempfile, math
from datetime import datetime
from typing import List

import torch
from celery import Celery
from sqlalchemy.orm import Session

from common.config import settings
from common.db import SessionLocal, engine, Base
from common.models import Job, JobStatus, Artifact
from common.storage import get_minio

Base.metadata.create_all(bind=engine)

celery_app = Celery("worker-gpu", broker=settings.redis_url, backend=settings.redis_url)

def _tensor_embed(image_bytes: bytes):
    # toy "embedding": mean RGB per channel -> 3-dim; then tile to 32 dims
    from PIL import Image
    import numpy as np
    im = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224,224))
    arr = np.array(im).astype("float32")/255.0
    means = arr.mean(axis=(0,1))  # R,G,B
    emb = np.tile(means, 11)[:32]  # 32-dim
    return emb.tolist()

@celery_app.task(name="worker.gpu.process_job", bind=True)
def process_job(self, job_id: str):
    # GPU queue handles 'embed_frames' or 'thumbnail' with toy embedding
    with SessionLocal() as db:
        job = db.get(Job, uuid.UUID(job_id))
        if not job:
            return
        job.status = JobStatus.processing
        job.updated_at = datetime.utcnow()
        db.commit()

        client = get_minio()

        # locate source object
        source_key = None
        objects = client.list_objects(settings.media_bucket, recursive=True)
        for obj in objects:
            if obj.object_name.startswith(job.media_id):
                source_key = obj.object_name
                break
        if not source_key:
            job.status = JobStatus.failed
            job.error = "Source object not found in media bucket"
            db.commit()
            return

        try:
            resp = client.get_object(settings.media_bucket, source_key)
            data = resp.read()
            resp.close(); resp.release_conn()

            ops = json.loads(job.operations)

            produced = []
            if "embed_frames" in ops or "thumbnail" in ops:
                # create thumbnail and embedding from first frame (or image)
                tmpdir = tempfile.mkdtemp()
                from PIL import Image
                with open(os.path.join(tmpdir, "src.bin"), "wb") as f:
                    f.write(data)
                # Try to load with PIL (works for images; for videos you'd extract frames with ffmpeg).
                try:
                    im = Image.open(io.BytesIO(data)).convert("RGB")
                except Exception:
                    # If it's a video, we could extract a frame using ffmpeg here (omitted for brevity).
                    raise RuntimeError("GPU worker demo expects image input for now.")
                # save thumbnail
                thumb_path = os.path.join(tmpdir, f"{job.media_id}_gpu_thumb.jpg")
                im2 = im.copy(); im2.thumbnail((320,320)); im2.save(thumb_path, "JPEG", quality=90)
                produced.append(("thumbnail_gpu", thumb_path))

                # compute toy embedding
                emb = _tensor_embed(data)
                import json as _json, tempfile as _tempfile
                emb_path = os.path.join(tmpdir, f"{job.media_id}_emb.json")
                with open(emb_path, "w") as f:
                    _json.dump({"embedding_dim": len(emb), "vector": emb}, f)
                produced.append(("embedding", emb_path))

                # upload produced artifacts
                for kind, path in produced:
                    key = f"{job.media_id}/{os.path.basename(path)}"
                    content_type = "application/json" if path.endswith(".json") else "image/jpeg"
                    client.fput_object(settings.outputs_bucket, key, path, content_type=content_type)
                    size = os.path.getsize(path)
                    with SessionLocal() as dbi:
                        a = Artifact(job_id=job.id, media_id=job.media_id, kind=kind, object_key=f"{settings.outputs_bucket}/{key}", size_bytes=size)
                        dbi.add(a); dbi.commit()

                job.status = JobStatus.done
                job.updated_at = datetime.utcnow()
                db.commit()

        except Exception as e:
            job.status = JobStatus.failed
            job.error = str(e)
            db.commit()
