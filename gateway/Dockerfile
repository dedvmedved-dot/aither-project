# Aither Gateway — production image
# CHANGE-0022
FROM python:3.12-slim

LABEL org.aither.component=gateway
LABEL org.aither.change=CHANGE-0022

# Non-root user
RUN groupadd -r aither -g 1000 && useradd -r -g aither -u 1000 -d /app aither

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY config.py .
COPY auth.py .
COPY routing.py .
COPY rate_limit.py .
COPY billing.py .
COPY usage.py .
COPY catalog.py .
COPY security.py .
COPY security_egress.py .
COPY vault.py .
COPY admin.py .
COPY metrics.py .
COPY hybrid_rag.py .
COPY wiki_graph.py .
COPY reaper.py .
COPY siem.py .
COPY token_estimator.py .
COPY catalog.yaml .

# Create writable dirs for non-root
RUN mkdir -p /tmp /var/log/aither && chown -R aither:aither /app /tmp /var/log/aither

USER aither

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
