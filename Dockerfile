FROM python:3.12-slim

LABEL maintainer="Vamsi Muddada"
LABEL description="ARGUS — Alert Response & Guardian Unified System"

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for local fallback storage
RUN mkdir -p /app/data/alerts

EXPOSE 5000

# Run with gunicorn in production
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app.main:app"]
