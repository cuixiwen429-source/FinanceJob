# FinanceJob Dashboard — Deployable container
FROM python:3.12-slim

# Install Node.js (required to build Next.js dashboard)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (node_modules and local dist are excluded by .dockerignore)
COPY . .

# Install Node dependencies and build dashboard
RUN cd dashboard && npm ci && npm run build

# Create data directories
RUN mkdir -p data/resumes data/eml_drafts shared

# Expose port (Render sets PORT env var)
EXPOSE 10000

# Seed DB from local cache if empty, then start API server
CMD ["python", "scripts/seed_and_serve.py"]
