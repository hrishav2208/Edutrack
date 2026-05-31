"""Gunicorn WSGI production server configuration."""

import multiprocessing

# Bind address and port
bind = "0.0.0.0:5000"

# Performance tuning: workers and threads
# Recommended worker count formula: 2 workers per CPU core + 1
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2

# Connection safety limits
timeout = 120
keepalive = 2

# Logging configuration
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
