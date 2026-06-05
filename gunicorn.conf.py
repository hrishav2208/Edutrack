"""Gunicorn WSGI production server configuration."""

import os
import multiprocessing

# Bind address and port (dynamically fetched for Railway/Render)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Performance tuning: workers and threads
# Render free tier has a 512MB memory limit, so we hardcode to 2 workers to prevent Out-Of-Memory crashes.
workers = 2
threads = 4

# Connection safety limits
timeout = 120
keepalive = 2

# Logging configuration
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
