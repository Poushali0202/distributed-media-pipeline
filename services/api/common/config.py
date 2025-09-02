import os
from pydantic import BaseModel

class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://media:media@localhost:5432/media")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minio")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minio12345")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    media_bucket: str = os.getenv("MEDIA_BUCKET", "media")
    outputs_bucket: str = os.getenv("OUTPUTS_BUCKET", "outputs")

settings = Settings()
