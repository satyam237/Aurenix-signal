FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY data ./data
COPY scripts ./scripts

RUN pip install --no-cache-dir -e .

# Cloud Scheduler owns timing; --force bypasses the UTC hour gate in cron_runner.
CMD ["python", "-m", "backend.scheduler.cron_runner", "--force"]
