# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=prod
ENV FLASK_APP=wsgi.py

WORKDIR /app

# Install system dependency utilities required for building packages (e.g. psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files to container
COPY . .

# Expose port 5000 for server binding
EXPOSE 5000

# Create a startup script that runs migrations then starts the server
RUN echo '#!/bin/sh\nflask db upgrade\nexec gunicorn -c gunicorn.conf.py wsgi:app' > /app/start.sh && chmod +x /app/start.sh

# Run migrations then start Gunicorn
CMD ["/app/start.sh"]
