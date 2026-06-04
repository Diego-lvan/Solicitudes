#!/bin/sh
# Container entrypoint for single-container deploys (Railway).
# Collects static files, applies migrations, then hands off to gunicorn
# bound to the platform-provided $PORT.
set -e

# The persistent volume mounts at /app/media owned by root; hand it (and the
# static dir) to the app user so the non-root gunicorn workers can write uploads.
echo "==> fixing ownership of /app/media and /app/staticfiles"
chown -R app:app /app/media /app/staticfiles 2>/dev/null || true

echo "==> collectstatic"
# Ignore the Tailwind source (app.css holds `@import "tailwindcss"`, which the
# manifest storage can't resolve). Only the compiled app.build.css is served.
python manage.py collectstatic --noinput --ignore app.css

echo "==> migrate"
python manage.py migrate --noinput

echo "==> starting gunicorn on port ${PORT:-8000} (workers drop to user 'app')"
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout 60 \
    --user app --group app
