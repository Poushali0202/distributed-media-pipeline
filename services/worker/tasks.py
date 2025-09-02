import os
import io
import json
import uuid
import shutil
import subprocess
import tempfile
from typing import List
from datetime import datetime

from celery import Celery
from sqlalchemy.orm import Session

from common.config import settings
from common.db import SessionLocal, engine, Base
from common.models import Job, JobStatus, Artifact
from common.storage import get_minio

# ensure tables exist (worker may start before api)
Base.metadata.create_all(bind=engine)

celery_app = Celery("worker", broker=settings.redis_url, backend=settings.redis_url)

def _is_video(filename: str) -> bool:
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    return ext in {"mp4", "mov", "mkv", "webm", "avi"}

@celery_app.task(name="worker.tasks.process_job", bind=True)
def process_job(self, job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, uuid.UUID(job_id))
        if not job:
            return
        job.status = JobStatus.processing
        job.updated_at = datetime.utcnow()
        db.commit()

        client = get_minio()

        # find source object by media_id: iterate bucket (demo) or infer naming
        # For demo simplicity, assume filename is unknown -> find most recent object starting with media_id
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

        # download to temp
        tmpdir = tempfile.mkdtemp()
        src_path = os.path.join(tmpdir, os.path.basename(source_key))
        try:
            response = client.get_object(settings.media_bucket, source_key)
            with open(src_path, "wb") as f:
                shutil.copyfileobj(response, f)
            response.close()
            response.release_conn()

            operations: List[str] = json.loads(job.operations)

            produced = []

            if _is_video(src_path):
                if "transcode_480p" in operations:
                    out_mp4 = os.path.join(tmpdir, f"{job.media_id}_480p.mp4")
                    cmd = ["ffmpeg", "-y", "-i", src_path, "-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", out_mp4]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    produced.append(("transcode_480p", out_mp4))

                if "thumbnail" in operations:
                    thumb = os.path.join(tmpdir, f"{job.media_id}_thumb.jpg")
                    cmd = ["ffmpeg", "-y", "-ss", "00:00:03", "-i", src_path, "-frames:v", "1", "-vf", "scale=320:-1", thumb]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    produced.append(("thumbnail", thumb))
            else:
                # image branch
                from PIL import Image
                if "thumbnail" in operations:
                    thumb = os.path.join(tmpdir, f"{job.media_id}_thumb.jpg")
                    im = Image.open(src_path)
                    im.thumbnail((320, 320))
                    im.save(thumb, "JPEG", quality=90)
                    produced.append(("thumbnail", thumb))

            # upload produced
            for kind, path in produced:
                key = f"{job.media_id}/{os.path.basename(path)}"
                client.fput_object(settings.outputs_bucket, key, path, content_type="image/jpeg" if path.endswith(".jpg") else "video/mp4")
                size = os.path.getsize(path)
                # upsert artifact
                with SessionLocal() as dbi:
                    a = Artifact(job_id=job.id, media_id=job.media_id, kind=kind, object_key=f"{settings.outputs_bucket}/{key}", size_bytes=size)
                    dbi.add(a)
                    dbi.commit()

            job.status = JobStatus.done
            job.updated_at = datetime.utcnow()
            db.commit()

        except subprocess.CalledProcessError as e:
            job.status = JobStatus.failed
            job.error = f"ffmpeg error: {e.stderr.decode('utf-8', 'ignore')[:400]}"
            db.commit()
        except Exception as e:
            job.status = JobStatus.failed
            job.error = str(e)
            db.commit()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
