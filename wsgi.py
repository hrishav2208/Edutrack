"""WSGI entry point for production servers (Gunicorn) and local debugging."""

import os
from app import create_app

# Load appropriate configuration profile (dev | prod | test)
env = os.environ.get("FLASK_ENV", "dev")
app = create_app(env)

if __name__ == "__main__":
    host = os.environ.get("EDUTRACK_HOST", "0.0.0.0")
    port = int(os.environ.get("EDUTRACK_PORT", "5000"))
    app.run(host=host, port=port)
