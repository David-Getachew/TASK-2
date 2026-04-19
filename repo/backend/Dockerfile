FROM python:3.10-slim AS base

WORKDIR /app

# System dependencies for psycopg2, cryptography, Pillow, reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY database/ ./database/
COPY alembic.ini .

# Test files are included so `pytest unit_tests/` and `pytest api_tests/` work inside the container
COPY unit_tests/ ./unit_tests/
COPY api_tests/ ./api_tests/
COPY conftest.py .
COPY pytest.ini .
COPY seed_demo.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Frontend dist is mounted at runtime via volume (see docker-compose.yml)
ENV FRONTEND_DIST_PATH=/app/frontend_dist

EXPOSE 8443

# entrypoint.sh runs `alembic upgrade head` before starting uvicorn so a
# fresh container boot can bring up an empty database without an out-of-
# band migration step. Set SKIP_MIGRATIONS=1 in the test harness if the
# test fixture manages its own schema.
CMD ["./entrypoint.sh"]
