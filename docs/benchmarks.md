# Benchmarks (Example Template)

## Method
- Hardware: laptop (8 cores), Docker Desktop
- Dataset: 10 short videos (5–30s), 50 images
- Worker replicas: 1, 2, 4

## Results (example placeholders—replace with your measurements)
- 1 worker: 10 jobs/min, p95 latency 50s
- 2 workers: 18 jobs/min, p95 latency 35s
- 4 workers: 32 jobs/min, p95 latency 22s

## Notes
- Throughput scales ~linearly until CPU saturation.
- ffmpeg preset and CRF strongly impact speed/quality.
