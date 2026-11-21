# ARGUS — Alert Response & Guardian Unified System

A lightweight alert ingestion and monitoring API built with Flask, designed for cloud deployment on AWS EC2 with S3 storage.

## Features

- **REST API** — Create, list, acknowledge, resolve, and delete security alerts
- **Dashboard** — Real-time web dashboard showing alert status and statistics
- **S3 Integration** — Persists alert data to AWS S3 with local fallback storage
- **Dockerized** — Production-ready container with Gunicorn WSGI server
- **CI/CD** — GitHub Actions pipeline with automated testing and Docker image builds
- **Nginx** — Reverse proxy configuration included

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the app
flask --app app.main run --debug

# Run tests
pytest tests/ -v
```

### Docker

```bash
docker build -t argus .
docker run -p 5000:5000 --env-file .env argus
```

### API Usage

```bash
# Health check
curl http://localhost:5000/health

# Create an alert
curl -X POST http://localhost:5000/alerts \
  -H "Content-Type: application/json" \
  -d '{"title": "SSH brute force detected", "severity": "critical", "source": "ids"}'

# List all alerts
curl http://localhost:5000/alerts

# Filter by severity
curl http://localhost:5000/alerts?severity=critical

# Acknowledge an alert
curl -X POST http://localhost:5000/alerts/<alert_id>/acknowledge

# Resolve an alert
curl -X POST http://localhost:5000/alerts/<alert_id>/resolve

# Delete an alert
curl -X DELETE http://localhost:5000/alerts/<alert_id>
```

## Architecture

```
User → Nginx (:80) → Flask/Gunicorn (:5000) → S3 (alert storage)
```

## Project Structure

```
Argus/
├── app/
│   ├── __init__.py        # Package init
│   ├── main.py            # Flask app factory + entry point
│   ├── models.py          # Pydantic data models
│   ├── routes.py          # API endpoints
│   └── s3_client.py       # AWS S3 integration
├── templates/
│   └── dashboard.html     # Web dashboard
├── tests/
│   └── test_routes.py     # API tests
├── .github/workflows/
│   └── ci.yml             # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
└── README.md
```

## Deployment

See the deployment guide for instructions on deploying to AWS EC2 with Nginx reverse proxy and S3 storage.

## License

MIT
