#!/bin/sh
set -e

echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

python << 'PYEOF'
import sys, time, os
import psycopg2

host     = os.environ.get('DB_HOST', 'db')
port     = int(os.environ.get('DB_PORT', 5432))
dbname   = os.environ.get('DB_NAME', 'efootball_rewards')
user     = os.environ.get('DB_USER', 'efootball')
password = os.environ.get('DB_PASSWORD', 'efootball_secret')

for attempt in range(1, 31):
    try:
        conn = psycopg2.connect(
            host=host, port=port,
            dbname=dbname, user=user, password=password,
            connect_timeout=3,
        )
        conn.close()
        print(f"[entrypoint] PostgreSQL ready (attempt {attempt}).")
        sys.exit(0)
    except psycopg2.OperationalError as e:
        print(f"[entrypoint] Not ready yet ({e}). Retry {attempt}/30 in 2s...")
        time.sleep(2)

print("[entrypoint] ERROR: PostgreSQL unreachable after 30 attempts. Aborting.")
sys.exit(1)
PYEOF

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
