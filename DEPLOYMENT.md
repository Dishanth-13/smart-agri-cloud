# smart-agri-cloud Deployment Guide

This guide covers local development, testing, and production deployment strategies.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Quick Start with Makefile](#quick-start-with-makefile)
3. [API Testing](#api-testing)
4. [Database Management](#database-management)
5. [Training ML Models](#training-ml-models)
6. [Simulator Integration](#simulator-integration)
7. [Dashboard Usage](#dashboard-usage)
8. [Production Deployment](#production-deployment)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

## Local Development Setup

### Requirements

- **Docker**: v20.10+
- **Docker Compose**: v2.0+
- **Python**: 3.11+ (for local ML training/simulator)
- **curl** or **Postman**: For API testing
- **PostgreSQL Client** (optional): `psql` for direct DB access

### Initial Setup

```bash
# Clone repository (or navigate to workspace)
cd smart-agri-cloud

# Copy environment template
cp .env.example .env

# Verify Docker and Docker Compose
docker --version
docker compose version
```

### Environment Configuration

Edit `.env` to customize:

```bash
# Database credentials (change for production)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smart_agri

# API settings
API_HOST=0.0.0.0
API_PORT=8000

# ML Model path (inside container)
MODEL_PATH=/app/models/crop_rf.joblib

# Dashboard/PgAdmin credentials
PGADMIN_DEFAULT_EMAIL=admin@local
PGADMIN_DEFAULT_PASSWORD=admin

# Simulator settings (for testing)
SIMULATOR_INTERVAL=2          # seconds between data points
SIMULATOR_COUNT=0             # 0 = infinite, N = stop after N readings
```

## Quick Start with Makefile

The `Makefile` provides convenient commands for common tasks:

```bash
# Start all services (database, API, dashboard, pgadmin)
make up

# Stop services (keep data in volumes)
make down

# Stop and remove all volumes (clean slate)
make down-clean

# View logs in real-time
make logs

# Show container status
make status
```

### Access Services After `make up`

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Docs** | http://localhost:8000/docs | — |
| **Dashboard** | http://localhost:8501 | — |
| **PgAdmin** | http://localhost:8080 | admin@local / admin |
| **Database** | localhost:5432 | postgres / postgres |

## API Testing

### Test Endpoints with Makefile

```bash
# Health check
make test-health
# Output: {"status": "ok"}

# Ingest sensor reading
make test-ingest
# Output: {"id": 1, "ts": "2025-11-11T18:17:49.098046+00:00"}

# Predict crop recommendation
make test-predict
# Output: {"predictions": [{"crop": "Rice", "probability": 0.45}, ...]}
```

### Manual Testing with curl

**GET /health**
```bash
curl http://localhost:8000/health | jq
```

**POST /ingest** (Single reading)
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "sensor_001",
    "farm_id": 1,
    "temperature": 28.0,
    "humidity": 70.0,
    "ph": 6.5,
    "rainfall": 110.0,
    "n": 55,
    "p": 45,
    "k": 40
  }' | jq
```

**POST /predict** (By farm)
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"farm_id": 1}' | jq
```

**POST /predict** (By features)
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "N": 50, "P": 40, "K": 35,
      "temperature": 25.5, "humidity": 65.0,
      "ph": 6.8, "rainfall": 100.0
    }
  }' | jq
```

### Interactive API Testing

Visit **http://localhost:8000/docs** for interactive Swagger UI where you can:
- See all endpoints and their schemas
- Test endpoints directly in the browser
- View request/response examples

## Database Management

### Access Database with psql

```bash
# Via Makefile
make db-shell

# Or manually
docker compose exec db psql -U postgres -d smart_agri
```

### Common Database Queries

```sql
-- Show all tables
\dt

-- View readings table
SELECT * FROM readings LIMIT 10;

-- View farms
SELECT * FROM farms;

-- Count readings by farm
SELECT farm_id, COUNT(*) as reading_count 
FROM readings 
GROUP BY farm_id;

-- Latest reading per farm
SELECT DISTINCT ON (farm_id) farm_id, ts, temperature, humidity 
FROM readings 
ORDER BY farm_id, ts DESC;

-- Schema info
\dt+ readings
```

### PgAdmin Web Interface

1. Navigate to **http://localhost:8080**
2. Login: `admin@local` / `admin`
3. Right-click "Servers" → "Register Server"
4. Settings:
   - Name: `smart-agri-cloud`
   - Hostname: `db`
   - Port: `5432`
   - Username: `postgres`
   - Password: `postgres`
5. Browse tables and data in web UI

## Training ML Models

### Using Kaggle Dataset

1. **Download Dataset**
   ```bash
   # Option 1: Manual download from Kaggle
   # https://www.kaggle.com/atharvaingle/crop-recommendation-dataset
   # Save as: ml/data/crop_recommendation.csv
   
   # Option 2: Use Kaggle CLI
   pip install kaggle
   kaggle datasets download -d atharvaingle/crop-recommendation-dataset
   unzip crop-recommendation-dataset.zip -d ml/data/
   ```

2. **Train Model Locally**
   ```bash
   # Install Python dependencies
   pip install -r ml/requirements.txt
   
   # Train and save model
   python ml/train.py
   # Output: ✓ Model trained and saved to ml/models/crop_rf.joblib
   ```

3. **Verify Model**
   ```bash
   ls -lh ml/models/crop_rf.joblib
   ```

4. **Reload in API**
   ```bash
   # Restart API container to load new model
   docker compose restart api
   
   # Verify with /predict endpoint
   make test-predict
   ```

### Generate Dummy Model (For Testing)

```bash
python ml/gen_dummy_model.py
# Creates mock model at ml/models/crop_rf.joblib
```

## Simulator Integration

### Run Continuous Data Simulator

Generate realistic fake sensor data streaming to the API:

```bash
# Start simulator (infinite)
make simulator-run

# Or run in background
python simulator/simulator.py &

# Control via environment variables
SIMULATOR_INTERVAL=2 SIMULATOR_COUNT=100 python simulator/simulator.py
```

The simulator will:
- Generate readings every `SIMULATOR_INTERVAL` seconds
- Post to `/ingest` endpoint
- Create 5 different sensor IDs
- Populate readings with realistic agricultural values

### Monitor Simulator

In another terminal:

```bash
# Check recent readings
docker compose exec db psql -U postgres -d smart_agri \
  -c "SELECT COUNT(*) as total_readings FROM readings;"

# Watch live ingestion
watch "docker compose exec -T db psql -U postgres -d smart_agri \
  -c 'SELECT COUNT(*) FROM readings;'"
```

## Dashboard Usage

Access at **http://localhost:8501**

### Dashboard Features

1. **Recent Readings Table**
   - Shows last 20 sensor readings
   - Displays timestamp, sensor_id, farm_id, and measurements

2. **Prediction**
   - Select farm_id from sidebar
   - Click "Predict" button
   - View top crop recommendations

3. **Auto-Refresh**
   - Data cached for 10 seconds
   - Manually refresh with button

### Dashboard Code Structure

- `services/dashboard/streamlit_app.py`: Main app
- Connects to PostgreSQL to read readings
- Calls API `/predict` endpoint
- Uses Streamlit cache for performance

## Production Deployment

### Pre-Production Checklist

```
[ ] Change .env passwords (database, pgadmin)
[ ] Train ML model with production data
[ ] Set API_PORT to 80 or 443 (with reverse proxy)
[ ] Configure external PostgreSQL (AWS RDS, Azure, etc.)
[ ] Enable HTTPS/TLS for all endpoints
[ ] Add API authentication (JWT tokens)
[ ] Configure database backups
[ ] Set up monitoring and alerting
[ ] Enable structured logging (ELK, Datadog)
[ ] Use Docker image registries (Docker Hub, ECR, etc.)
[ ] Deploy with container orchestration (Kubernetes, Swarm)
```

### Option 1: AWS Deployment (Recommended)

**Architecture:**
- RDS PostgreSQL + TimescaleDB extension
- ECS Fargate for API service
- CloudFront + ALB for load balancing
- Streamlit on EC2 or Fargate
- S3 for ML model storage

**Setup Steps:**
1. Create RDS PostgreSQL instance with TimescaleDB extension
2. Update `DATABASE_URL` in `.env`
3. Push Docker images to ECR
4. Create ECS task definitions for api and dashboard
5. Configure ALB for routing
6. Deploy with `docker compose` or Kubernetes manifests

### Option 2: Kubernetes Deployment

**Create Helm Chart:**

```bash
# Create k8s manifests
mkdir k8s/
```

**Typical structure:**
```
k8s/
├── api-deployment.yaml
├── api-service.yaml
├── db-statefulset.yaml
├── dashboard-deployment.yaml
├── configmap.yaml
└── secret.yaml (PostgreSQL creds)
```

**Deploy:**
```bash
kubectl apply -f k8s/
```

### Option 3: Single Server (VPS/VM)

**On your server:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Clone project
git clone <repo-url> smart-agri-cloud
cd smart-agri-cloud

# Update .env with production values
nano .env

# Start with docker-compose
docker compose up -d

# Add reverse proxy (nginx)
# Configure SSL certificates (Let's Encrypt)
# Set up monitoring (Prometheus, Grafana)
```

### Backup Strategy

**Automated PostgreSQL Backups:**
```bash
# Daily backup to S3
docker compose exec db pg_dump -U postgres smart_agri | \
  aws s3 cp - s3://my-backups/smart-agri-$(date +%Y%m%d).sql
```

**Add to crontab:**
```
0 2 * * * cd /opt/smart-agri-cloud && \
  docker compose exec -T db pg_dump -U postgres smart_agri | \
  gzip > /backups/smart-agri-$(date +\%Y\%m\%d).sql.gz
```

## Monitoring & Troubleshooting

### View Logs

```bash
# All services
make logs

# Specific service
docker compose logs api --tail 50 -f

# Database
docker compose logs db --tail 100
```

### Common Issues

#### "Connection refused" from API to Database
```bash
# Wait for DB to finish initializing (15-30 seconds)
docker compose logs db | grep "ready"

# Or restart API after DB is ready
docker compose restart api
```

#### `/predict` returns demo predictions
```bash
# Model file missing
ls -lh ml/models/crop_rf.joblib

# Train a new model
python ml/train.py

# Or generate dummy
python ml/gen_dummy_model.py

# Restart API to reload
docker compose restart api
```

#### Dashboard won't load
```bash
# Check API is running
curl http://localhost:8000/health

# Check database connection
docker compose logs api | grep "database"

# Restart dashboard
docker compose restart dashboard
```

### Performance Monitoring

**Database Query Performance:**
```sql
-- Slow queries in TimescaleDB
SELECT * FROM pg_stat_statements 
WHERE mean_exec_time > 100 
ORDER BY total_exec_time DESC;
```

**Container Resource Usage:**
```bash
docker stats
```

**Network Connectivity:**
```bash
docker compose exec api ping db
docker compose exec api curl http://db:5432/
```

### Scaling Considerations

**For High Throughput:**
1. **Database**: Replicate TimescaleDB with streaming replication
2. **API**: Run multiple instances with load balancer
3. **Cache**: Add Redis for reading cache
4. **Async**: Use Celery for long-running predictions
5. **Metrics**: Add Prometheus + Grafana

**Example Multi-Instance Setup:**
```yaml
services:
  api-1:
    # ...
  api-2:
    # ...
  nginx:
    image: nginx
    ports:
      - "8000:80"
    # upstream to api-1, api-2
```

## Support & Debugging

For detailed API information:
- Visit http://localhost:8000/docs (Swagger UI)
- View http://localhost:8000/redoc (ReDoc)

For database issues:
- Use PgAdmin at http://localhost:8080
- Run diagnostic queries in `make db-shell`

Check logs for errors:
```bash
docker compose logs --tail 200 api | grep -i error
```

---

**Last Updated**: November 2025
**Version**: 1.0
