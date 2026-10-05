# Build context is the repository root so the seed scripts can read sample-data/.
FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY sample-data /srv/sample-data

# The SQLite database lives in data/, which docker-compose.yml mounts as a volume.
RUN adduser -D -u 10001 appuser && mkdir -p data && chown appuser data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
