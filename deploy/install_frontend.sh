#!/usr/bin/env bash
# Install a frontend build (tar.gz of frontend/dist) into /var/www/alborz-frontend (run as root)
# usage: sudo ./deploy/install_frontend.sh /tmp/alborz-frontend.tar.gz
set -euo pipefail
archive="$1"
target=/var/www/alborz-frontend
staging="$(mktemp -d /var/www/.alborz-frontend.XXXX)"
tar -xzf "$archive" -C "$staging"
test -f "$staging/index.html"
chmod -R a+rX "$staging"
# Keep the previous build to roll back with: mv /var/www/alborz-frontend.previous /var/www/alborz-frontend
rm -rf "$target.previous"
if [ -d "$target" ]; then mv "$target" "$target.previous"; fi
mv "$staging" "$target"
echo "Frontend installed in $target"
