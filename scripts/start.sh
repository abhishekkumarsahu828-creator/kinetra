#!/bin/sh
set -eu
python manage.py migrate --noinput
if [ "${KINETRA_CREATE_SUPERUSER_ONCE:-}" = "yes" ]; then
    python manage.py bootstrap_superuser
fi
python manage.py collectstatic --noinput
exec gunicorn kinetra.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-3}" --threads "${WEB_THREADS:-4}" --timeout 60 --access-logfile - --error-logfile -
