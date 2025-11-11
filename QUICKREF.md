# Smart Agri Cloud - Quick Reference

## Commands Cheat Sheet

### Service Management
```bash
make up              # Start all services
make down            # Stop services (keep data)
make down-clean      # Stop and delete data
make restart         # Restart all services
make status          # Show container status
make logs            # Stream all logs
```

### Testing
```bash
make test-health     # GET /health
make test-ingest     # POST /ingest (sample data)
make test-predict    # POST /predict (farm_id=1)
```

### Container Access
```bash
make api-shell       # Shell in API container
make dashboard-shell # Shell in dashboard
make db-shell        # psql terminal
```

### Development
```bash
make simulator-run   # Start data simulator
make build           # Build images only
make clean           # Remove everything
```

---

## Service URLs

| Service | URL | Login |
|---------|-----|-------|
| **API** | http://localhost:8000 | — |
| **API Docs** | http://localhost:8000/docs | — |
| **Dashboard** | http://localhost:8501 | — |
| **PgAdmin** | http://localhost:8080 | admin@local / admin |
| **Database** | localhost:5432 | postgres / postgres |

---

## API Endpoints

### `/health` (GET)
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### `/ingest` (POST)
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"sensor_id":"s1","farm_id":1,"temperature":28,"humidity":70,"ph":6.5,"rainfall":110,"n":55,"p":45,"k":40}'
# {"id": 1, "ts": "2025-11-11T..."}
```

### `/predict` (POST)
```bash
# By farm (queries latest reading)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"farm_id":1}'

# By features
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":{"N":50,"P":40,"K":35,"temperature":25.5,"humidity":65,"ph":6.8,"rainfall":100}}'

# Response
# {"predictions":[{"crop":"Rice","probability":0.45},{"crop":"Maize","probability":0.35},{"crop":"Wheat","probability":0.2}]}
```

---

## Database Schema

**readings** (TimescaleDB Hypertable)
```
ts          TIMESTAMP (PK, partitioning key)
id          BIGSERIAL (PK)
sensor_id   TEXT
farm_id     INT (FK → farms)
temperature FLOAT
humidity    FLOAT
ph          FLOAT
rainfall    FLOAT
n, p, k     FLOAT
```

**farms**
```
id       SERIAL (PK)
name     TEXT
location TEXT
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused (5432) | `docker compose logs db` - wait for DB to init |
| API won't start | `docker compose logs api` - check DB connection |
| /predict returns demo | Model missing - run `python ml/train.py` |
| Dashboard won't load | Check API health: `make test-health` |
| Need to view data | `make db-shell` then `SELECT * FROM readings LIMIT 10;` |

---

## Project Structure

```
smart-agri-cloud/
├── services/api/          # FastAPI backend (port 8000)
├── services/dashboard/    # Streamlit frontend (port 8501)
├── db/schema.sql         # Database schema
├── ml/train.py           # Model training
├── simulator/simulator.py # Test data generator
├── docker-compose.yml    # Orchestration
├── .env                  # Configuration
└── Makefile             # Commands
```

---

## Environment Variables

Edit `.env` file to configure:

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

# Web Interfaces
PGADMIN_DEFAULT_EMAIL=admin@local
PGADMIN_DEFAULT_PASSWORD=admin

# Simulator
SIMULATOR_INTERVAL=2
SIMULATOR_COUNT=0
```

---

## Common Workflows

### Start Fresh
```bash
make down-clean
make up
```

### Train & Deploy Model
```bash
python ml/train.py
docker compose restart api
make test-predict
```

### Monitor Live Data
```bash
# Terminal 1: Stream logs
make logs

# Terminal 2: Start simulator
make simulator-run

# Terminal 3: Monitor data
watch "docker compose exec -T db psql -U postgres -d smart_agri -c 'SELECT COUNT(*) FROM readings;'"
```

### Debug API Issue
```bash
# View logs
docker compose logs api --tail 100 -f

# Access container
make api-shell

# Run Python commands
python -c "from app.database import SessionLocal; db = SessionLocal(); print(db.query(..all())"
```

---

## Performance Tips

- Use `make up` (includes build)
- Always wait 10 seconds after `make up` before testing
- Monitor with `make logs` in background
- Check `make status` to verify all containers running
- Use `make clean` if something corrupts

---

## Next Steps

1. **Deploy Model**: `python ml/train.py`
2. **Test Everything**: `make test-health && make test-ingest && make test-predict`
3. **Start Simulator**: `make simulator-run`
4. **View Dashboard**: http://localhost:8501
5. **Read Guides**: README.md, DEPLOYMENT.md, DEVELOPER.md

---

## Documentation

- **README.md** - Overview & quick start
- **DEPLOYMENT.md** - Production deployment guide
- **DEVELOPER.md** - Development guidelines
- **VERIFICATION_REPORT.md** - Detailed verification

---

For help: Review the detailed guides or check API docs at http://localhost:8000/docs
