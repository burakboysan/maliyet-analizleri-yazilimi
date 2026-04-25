#!/usr/bin/env bash
set -euo pipefail

TARGET="/etc/nginx/sites-available/fastapi"
BACKUP="/etc/nginx/sites-available/fastapi.bak_20260406"

sudo cp "$TARGET" "$BACKUP"

sudo python3 - <<'PY'
from pathlib import Path

path = Path("/etc/nginx/sites-available/fastapi")
text = path.read_text()
needle = "    server_name 34.163.117.71 _;\n"
insert = "    server_name 34.163.117.71 _;\n    client_max_body_size 20M;\n"

if "client_max_body_size 20M;" not in text:
    if needle not in text:
        raise SystemExit("server_name satiri bulunamadi")
    text = text.replace(needle, insert, 1)
    path.write_text(text)
PY

sudo nginx -t
sudo systemctl reload nginx
echo "OK"
sudo cat "$TARGET"
