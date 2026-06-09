FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint to /entrypoint.sh — OUTSIDE /app so the volume mount
# (- .:/app) does NOT override it and Windows NTFS permissions don't affect it.
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

COPY . .

RUN mkdir -p /app/staticfiles /app/media /app/logs

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
