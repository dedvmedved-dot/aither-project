# =====================================================================
# Aither BFF — authoritative source: ../../services/portal-backend/app/main.py
# This Dockerfile builds from the single authoritative BFF source.
# bff-prod/app.py is SUPERSEDED (archived, excluded from build context).
# =====================================================================
FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

# Non-root user for production (CHANGE-0022-C5)
RUN groupadd -r bff -g 1000 && useradd -r -g bff -u 1000 -d /app bff

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

# Fix ownership for non-root execution
RUN chown -R bff:bff /app

USER bff

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
