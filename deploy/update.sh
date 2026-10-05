#!/usr/bin/env bash
# Pull the latest main and apply it (run as the alborz user from /srv/alborz-backend)
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only origin main
./venv/bin/pip install -q -r requirements.txt
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput -v 0
sudo systemctl restart alborz-backend
echo "Deployed $(git rev-parse --short HEAD)"
