# =====================================================================
# Aither BFF — authoritative source: services/portal-backend/app/main.py
# This Dockerfile ACTUALLY copies from the authoritative BFF source.
# tools/bff/app.py is SUPERSEDED (excluded from build).
# =====================================================================
FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

RUN groupadd -r bff -g 1000 && useradd -r -g bff -u 1000 -d /app bff

WORKDIR /app

# Copy requirements from AUTHORITATIVE source (portal-backend)
COPY services/portal-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual authoritative source
COPY services/portal-backend/app/ ./app/

RUN chown -R bff:bff /app

USER bff

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
