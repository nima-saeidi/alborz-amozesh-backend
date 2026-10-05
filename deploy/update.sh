#!/usr/bin/env bash
# Pull the latest main and apply it (run as the alborz user from /srv/alborz-backend)
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only origin main
# files.pythonhosted.org is not reachable from the server: packages come from /srv/alborz-wheels
# (download new ones with: pip download -r requirements.txt --platform manylinux2014_x86_64 --python-version 3.14 --only-binary=:all: -d wheels)
./venv/bin/pip install -q --no-index --find-links /srv/alborz-wheels -r requirements.txt
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput -v 0
sudo systemctl restart alborz-backend
echo "Deployed $(git rev-parse --short HEAD)"
