FROM python:3.11-slim

WORKDIR /app

# Non-root user setup
RUN useradd -m appuser

# Install system dependencies if any required (e.g. for psycopg or others)
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Adjust permissions
RUN chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
