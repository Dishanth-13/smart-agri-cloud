# smart-agri-cloud

**Production-ready monorepo for IoT agricultural sensor data ingestion, ML-driven crop prediction, and real-time monitoring.**

## Overview

`smart-agri-cloud` provides:
- **API Service** (FastAPI + uvicorn): REST endpoints for sensor data ingestion, health checks, and crop predictions
- **TimescaleDB**: Time-series database for efficient sensor readings storage with hypertable partitioning
- **Streamlit Dashboard**: Real-time visualization and prediction interface
- **PgAdmin**: Web-based PostgreSQL administration tool
- **ML Module**: RandomForest model training on Kaggle crop recommendation dataset
- **Sensor Simulator**: Fake sensor data generator for testing

## Quick Start

### Prerequisites
- Docker & Docker Compose v2.0+
- Python 3.11+ (for local ML training)
- 2 GB+ available disk space

### 1. Clone and Configure

```bash
cd smart-agri-cloud
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 2. Start All Services

```bash
docker compose up -d --build
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **PgAdmin**: http://localhost:8080 (admin@local / admin)
- **Database**: localhost:5432 (postgres / postgres)

### 3. Verify Everything is Running

```bash
docker compose ps
```

Expected output: all 4 containers running (api, dashboard, db, pgadmin).

## API Endpoints

### `GET /health`
Health check endpoint. Returns `{"status": "ok"}` if API and database are operational.

```bash
curl http://localhost:8000/health
```

### `POST /ingest`
Ingest sensor readings into the database.

**Request body:**
```json
{
  "sensor_id": "sensor_001",
  "farm_id": 1,
  "temperature": 25.5,
  "humidity": 65.0,
  "ph": 6.8,
  "rainfall": 100.0,
  "n": 50,
  "p": 40,
  "k": 35
}
```

**Response:**
```json
{
  "id": 1,
  "ts": "2025-11-11T18:17:49.098046+00:00"
}
```

### `POST /predict`
Predict top crop recommendations based on farm or custom features.

**Request body (by farm ID):**
```json
{
  "farm_id": 1
}
```

**Request body (by custom features):**
```json
{
  "features": {
    "N": 50,
    "P": 40,
    "K": 35,
    "temperature": 25.5,
    "humidity": 65.0,
    "ph": 6.8,
    "rainfall": 100.0
  }
}
```

**Response:**
```json
{
  "predictions": [
    {"crop": "Rice", "probability": 0.45},
    {"crop": "Maize", "probability": 0.35},
    {"crop": "Wheat", "probability": 0.20}
  ]
}
```

## Architecture

### Database Schema

**readings** (hypertable)
- `ts`: Timestamp (partitioning key)
- `id`: Row ID
- `sensor_id`: Identifier
- `farm_id`: Foreign key to `farms`
- `temperature`, `humidity`, `ph`, `rainfall`, `n`, `p`, `k`: Sensor measurements

**farms**
- `id`: Primary key
- `name`: Farm name
- `location`: Farm location

Sample farms seeded on startup: Farm North, Farm South, Farm East, Farm West, Demo Farm.

### Services

| Service | Language | Framework | Port |
|---------|----------|-----------|------|
| API | Python 3.11 | FastAPI + SQLAlchemy + uvicorn | 8000 |
| Dashboard | Python 3.11 | Streamlit | 8501 |
| Database | PostgreSQL 14 | TimescaleDB | 5432 |
| PgAdmin | Web | pgAdmin4 | 8080 |

## Development & Testing

### Test Sensor Ingest

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id":"test_sensor",
    "farm_id":1,
    "temperature":28.0,
    "humidity":70.0,
    "ph":6.5,
    "rainfall":110.0,
    "n":55,
    "p":45,
    "k":40
  }'
```

### Run Sensor Simulator

Generates continuous fake sensor readings:

```bash
python simulator/simulator.py
```

Set `SIMULATOR_INTERVAL` (seconds) and `SIMULATOR_COUNT` (0 = infinite) in `.env`.

### Train ML Model Locally

Download the Kaggle Crop Recommendation dataset, place CSV at `ml/data/crop_recommendation.csv`, then:

```bash
python ml/train.py
```

This trains a RandomForest and saves to `ml/models/crop_rf.joblib`.

## Makefile Commands

Common tasks:

```bash
make up              # Start all services with build
make down            # Stop all services
make build           # Build images only
make api-shell       # Open shell in API container
make dashboard-shell # Open shell in dashboard container
make simulator-run   # Run simulator locally
```

## File Structure

```
smart-agri-cloud/
├── docker-compose.yml      # Orchestration
├── .env.example            # Environment template
├── .env                    # (local) Configuration
├── Makefile                # Common tasks
├── README.md               # This file
│
├── services/
│   ├── api/                # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py     # Endpoints & FastAPI app
│   │   │   ├── models.py   # SQLAlchemy ORM models
│   │   │   ├── schemas.py  # Pydantic request/response models
│   │   │   ├── database.py # DB connection & session factory
│   │   │   ├── config.py   # Settings
│   │   │   └── crud.py     # Database CRUD operations
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── pyproject.toml  # (optional) Poetry config
│   │
│   └── dashboard/          # Streamlit app
│       ├── streamlit_app.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── db/
│   └── schema.sql          # TimescaleDB schema & migrations
│
├── ml/
│   ├── train.py            # RandomForest trainer
│   ├── gen_dummy_model.py  # Dummy model generator for testing
│   ├── requirements.txt
│   ├── data/               # (local) Place crop_recommendation.csv here
│   └── models/
│       └── crop_rf.joblib  # Trained model (generated)
│
└── simulator/
    └── simulator.py        # Fake sensor data generator
```

## Environment Variables

See `.env.example` for all options:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smart_agri
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/smart_agri

# API
API_HOST=0.0.0.0
API_PORT=8000
MODEL_PATH=/app/models/crop_rf.joblib

# Dashboard/PgAdmin
PGADMIN_DEFAULT_EMAIL=admin@local
PGADMIN_DEFAULT_PASSWORD=admin

# Simulator
SIMULATOR_INTERVAL=2
SIMULATOR_COUNT=0  # 0 = infinite
```

## Troubleshooting

### "Connection refused" from API
- DB may still be initializing. Wait 10-15 seconds and retry.
- Check logs: `docker compose logs db`

### Predict endpoint returns demo predictions
- Model file (`ml/models/crop_rf.joblib`) is missing.
- Train locally with real data: `python ml/train.py`
- Or regenerate dummy: `python ml/gen_dummy_model.py`

### Dashboard won't load
- API must be running: `docker compose logs api`
- Verify database connection in API logs

## Production Deployment

For production use:
1. Use managed PostgreSQL + TimescaleDB (AWS RDS, Azure Database, etc.)
2. Set `DATABASE_URL` to external DB.
3. Use environment-specific `.env` files.
4. Run migrations with Alembic before service startup.
5. Add API authentication (JWT, API keys).
6. Deploy API & dashboard to Kubernetes or managed container services.
7. Add CI/CD (GitHub Actions, GitLab CI, etc.).
8. Monitor logs with ELK, Datadog, or CloudWatch.

## Contributing

1. Create feature branch
2. Test locally: `make up` → test endpoints
3. Submit PR

## License

MIT
