FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /data
COPY --chown=1000:1000 app/ ./app/
RUN chown -R 1000:1000 /data

EXPOSE 8000

USER 1000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
