FROM python:3.11-slim

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
