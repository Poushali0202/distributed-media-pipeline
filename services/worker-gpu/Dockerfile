# Optional GPU worker (stub). Use an NVIDIA base to enable GPUs:
# docker build --build-arg TORCH_CUDA=cu118 -t media-worker-gpu .
# docker run --gpus all media-worker-gpu

FROM python:3.11-slim

# For real GPU support, consider an NVIDIA CUDA runtime base image and install torch w/ CUDA.
# This demo installs CPU torch; code will use CUDA if available.
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir pillow==10.3.0 sqlalchemy==2.0.30 psycopg2-binary==2.9.9 minio==7.2.7 celery[redis]==5.3.6 pydantic==2.7.4

WORKDIR /app
COPY . /app
CMD ["celery", "-A", "tasks_gpu.celery_app", "worker", "--loglevel=INFO", "-Q", "gpu"]
