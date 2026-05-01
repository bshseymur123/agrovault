FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Create data directory for SQLite persistence
RUN mkdir -p /app/data

# Override DATABASE_URL to use persistent volume path
ENV DATABASE_URL=sqlite:////app/data/agrovault.db

# Entrypoint: seed if DB is empty, then launch
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
