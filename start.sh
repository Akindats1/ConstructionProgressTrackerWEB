#!/bin/sh
gunicorn --bind 0.0.0.0:8000 app.app:app &
exec caddy run --config /etc/caddy/Caddyfile
