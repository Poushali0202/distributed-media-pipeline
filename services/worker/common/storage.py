import io
import uuid
from minio import Minio
from .config import settings

def get_minio():
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    return client

def generate_media_id() -> str:
    return str(uuid.uuid4())

def object_key_for_media(media_id: str, filename: str) -> str:
    # keep extension
    return f"{media_id}{filename[filename.rfind('.'):]}" if '.' in filename else media_id
