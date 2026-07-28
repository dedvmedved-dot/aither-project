FROM python:3.11-slim

WORKDIR /app

# Copy requirements lock file with hashes
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY --chown=1000:1000 app/ ./app/

# Copy RAG training manual docs
COPY --chown=1000:1000 rag-docs/ /data/rag-docs/

EXPOSE 8000

USER 1000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]