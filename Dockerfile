# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y netcat-openbsd gcc libpq-dev

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Default: run dev server
CMD ["./start.sh", "gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000"]
