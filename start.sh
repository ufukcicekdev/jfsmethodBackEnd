#!/bin/bash
set -e

ROLE="${ROLE:-web}"

if [ "$ROLE" = "worker" ]; then
    echo "[start.sh] ROLE=worker → Bildirim scheduler başlatılıyor..."
    exec python manage.py run_worker
elif [ "$ROLE" = "cron" ]; then
    echo "[start.sh] ROLE=cron → Bildirim tetikleniyor..."
    exec python manage.py fire_scheduled_notifications
else
    echo "[start.sh] ROLE=web → Web sunucusu başlatılıyor..."
    exec gunicorn fizyotech.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
fi
