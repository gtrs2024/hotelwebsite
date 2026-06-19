#!/bin/bash
cd "$(dirname "$0")"
python3 database.py
PORT=${PORT:-8000}
exec python3 app.py
