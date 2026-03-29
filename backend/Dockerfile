FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["bash", "-c", "alembic upgrade head && python -m snep.seed; uvicorn snep.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
