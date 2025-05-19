#!/bin/sh
gunicorn --bind 0.0.0.0:8000 app.main:app &
exec caddy run --config /etc/caddy/Caddyfile
