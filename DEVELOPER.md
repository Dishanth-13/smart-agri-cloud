# Developer Guide - smart-agri-cloud

Complete guide for contributing to and extending the smart-agri-cloud project.

## Project Architecture

```
smart-agri-cloud (Monorepo)
├── services/
│   ├── api/           # FastAPI backend (port 8000)
│   └── dashboard/     # Streamlit frontend (port 8501)
├── ml/                # ML model training
├── simulator/         # Test data generator
├── db/                # Database schema & migrations
├── docker-compose.yml # Container orchestration
└── Makefile          # Development tasks
```

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend API | FastAPI | 0.100.0 |
| Server | uvicorn | 0.22.0 |
| ORM | SQLAlchemy | 2.0.20 |
| Validation | Pydantic | v2 |
| Database | PostgreSQL + TimescaleDB | 14 / 2.9.2 |
| Driver | psycopg2-binary | 2.9.7 |
| ML Framework | scikit-learn | 1.3.0 |
| Serialization | joblib | 1.3.2 |
| Dashboard | Streamlit | latest |
| Container | Docker + Docker Compose | 2.0+ |
| Language | Python | 3.11 |

## Getting Started

### Local Development Environment

```bash
# 1. Clone/navigate to project
cd smart-agri-cloud

# 2. Create Python virtual environment (optional, for local ML work)
python -m venv venv

# On Linux/macOS:
source venv/bin/activate

# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# 3. Install dependencies for local work
pip install -r ml/requirements.txt
pip install -r services/api/requirements.txt

# 4. Start Docker services
docker compose up -d --build

# 5. Verify services are running
docker compose ps
```

### IDE Setup (VS Code Recommended)

**Extensions:**
- Python (Microsoft)
- Pylance (Microsoft)
- Docker (Microsoft)
- REST Client (optional, for API testing)

**Settings (`.vscode/settings.json`):**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.pylintEnabled": true,
  "python.linting.pylintArgs": ["--load-plugins=pylint_django"],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python"
  }
}
```

## Code Structure & Conventions

### API Service (`services/api/`)

**Main entry point: `app/main.py`**
- FastAPI application instance
- All endpoint definitions
- Dependency injection (database sessions)

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db

app = FastAPI(title="smart-agri-cloud API")
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/ingest", response_model=ReadingResponse)
def ingest(reading: ReadingIn, db: Session = Depends(get_db)):
    # Handle sensor data ingestion
    pass
```

**Database layer: `app/database.py`**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Models: `app/models.py`**
```python
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Reading(Base):
    __tablename__ = "readings"
    
    id = Column(BigInteger, primary_key=True, index=True)
    ts = Column(DateTime, server_default=func.now())
    sensor_id = Column(String, index=True)
    temperature = Column(Float)
    # ... other fields
```

**Schemas: `app/schemas.py`**
```python
from pydantic import BaseModel
from typing import Optional

class ReadingIn(BaseModel):
    sensor_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    # ... all fields optional

class ReadingResponse(BaseModel):
    id: int
    ts: datetime
    
    class Config:
        from_attributes = True  # SQLAlchemy model conversion
```

### Database (`db/schema.sql`)

**Schema defines:**
- Tables: `farms`, `readings`, `sensors`, `models`
- Hypertable: `readings` partitioned by timestamp
- Constraints: Foreign keys with ON DELETE SET NULL
- Indexes: On frequently queried columns

Key aspects:
```sql
-- Time-series optimization
SELECT create_hypertable('readings', 'ts', if_not_exists => TRUE);

-- Composite primary key (required for TimescaleDB partitioning)
PRIMARY KEY (ts, id)

-- Foreign key with soft delete
FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE SET NULL
```

### ML Module (`ml/`)

**Training script: `train.py`**
```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

def load_data(path):
    """Load crop recommendation dataset"""
    df = pd.read_csv(path)
    return df

def train():
    """Train RandomForest model"""
    df = load_data('data/crop_recommendation.csv')
    X = df[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
    y = df['label']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    joblib.dump(model, 'models/crop_rf.joblib')
    print("✓ Model trained and saved")
```

**Dummy model generator: `gen_dummy_model.py`**
- Creates minimal trained model for testing
- Useful when real Kaggle dataset unavailable

### Dashboard (`services/dashboard/`)

**Streamlit app: `streamlit_app.py`**
```python
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# Page config
st.set_page_config(page_title="Agricultural Monitoring", layout="wide")

# Connect to database
engine = create_engine(DATABASE_URL)

@st.cache_data(ttl=10)
def load_recent_readings(limit=20):
    """Fetch recent sensor readings"""
    query = f"SELECT * FROM readings ORDER BY ts DESC LIMIT {limit}"
    df = pd.read_sql(query, engine)
    return df

# Display
st.title("Smart Agri Cloud Dashboard")
readings = load_recent_readings()
st.dataframe(readings)

# Prediction
farm_id = st.sidebar.number_input("Farm ID", value=1)
if st.button("Predict"):
    response = requests.post(
        "http://api:8000/predict",
        json={"farm_id": int(farm_id)}
    )
    st.json(response.json())
```

## Development Workflow

### Adding a New Endpoint

1. **Define Pydantic schema** (`app/schemas.py`):
```python
class MyNewRequest(BaseModel):
    field1: str
    field2: Optional[int] = None

class MyNewResponse(BaseModel):
    result: str
    status: str
```

2. **Add database model** (`app/models.py`) if needed:
```python
class MyModel(Base):
    __tablename__ = "my_table"
    # columns...
```

3. **Implement endpoint** (`app/main.py`):
```python
@app.post("/my-endpoint", response_model=MyNewResponse)
def my_endpoint(req: MyNewRequest, db: Session = Depends(get_db)):
    """Your endpoint description"""
    # Implementation
    return {"result": "...", "status": "ok"}
```

4. **Test**:
```bash
curl -X POST http://localhost:8000/my-endpoint \
  -H "Content-Type: application/json" \
  -d '{"field1": "value"}'
```

### Adding a Database Column

1. **Update schema** (`db/schema.sql`):
```sql
ALTER TABLE readings ADD COLUMN new_field FLOAT DEFAULT 0;
```

2. **Update SQLAlchemy model** (`app/models.py`):
```python
class Reading(Base):
    # ... existing fields ...
    new_field = Column(Float, default=0)
```

3. **Update Pydantic schema** (`app/schemas.py`):
```python
class ReadingIn(BaseModel):
    # ... existing fields ...
    new_field: Optional[float] = None
```

4. **Migrate database** (if using Alembic):
```bash
alembic revision --autogenerate -m "Add new_field to readings"
alembic upgrade head
```

### Code Style & Linting

**Format code:**
```bash
# Black formatter
pip install black
black services/api/app/

# isort for imports
pip install isort
isort services/api/app/
```

**Check style:**
```bash
pip install pylint
pylint services/api/app/main.py

pip install flake8
flake8 services/api/app/
```

## Testing

### Unit Tests

Create test files: `services/api/tests/test_*.py`

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ingest_reading():
    response = client.post("/ingest", json={
        "sensor_id": "test",
        "farm_id": 1,
        "temperature": 25.0,
        "humidity": 65.0,
        "ph": 6.8,
        "rainfall": 100.0,
        "n": 50,
        "p": 40,
        "k": 35
    })
    assert response.status_code == 200
    assert "id" in response.json()
```

**Run tests:**
```bash
pip install pytest
pytest services/api/tests/
```

### Integration Tests

Test full service communication:
```bash
# Start services
docker compose up -d

# Run integration tests
pytest tests/integration/

# Check all endpoints respond
make test-health
make test-ingest
make test-predict
```

## Debugging

### API Container

```bash
# Interactive shell
make api-shell
# or
docker compose exec api bash

# View logs
docker compose logs api --tail 100 -f

# Debug with pdb
docker compose exec api python -m pdb services/api/app/main.py
```

### Database Container

```bash
# psql shell
make db-shell

# Useful queries
SELECT * FROM readings ORDER BY ts DESC LIMIT 10;
SELECT COUNT(*) FROM readings;
```

### Dashboard Container

```bash
# Shell access
make dashboard-shell

# Streamlit logs
docker compose logs dashboard -f
```

### Python REPL in Container

```bash
docker compose exec api python

>>> from app.database import get_db
>>> from app import models
>>> db = next(get_db())
>>> readings = db.query(models.Reading).all()
>>> print(len(readings))
```

## Performance Optimization

### Database Query Optimization

**Add indexes:**
```sql
CREATE INDEX idx_readings_ts ON readings(ts DESC);
CREATE INDEX idx_readings_farm_id ON readings(farm_id);
```

**Use EXPLAIN to analyze queries:**
```sql
EXPLAIN ANALYZE SELECT * FROM readings WHERE farm_id = 1 ORDER BY ts DESC;
```

### Caching Strategies

**API caching** (with Redis):
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_farm_predictions(farm_id: int):
    # Expensive operation
    pass
```

**Dashboard caching** (Streamlit):
```python
@st.cache_data(ttl=600)  # 10 minute cache
def load_readings():
    return pd.read_sql(query, engine)
```

### Async Endpoints

Long-running predictions:
```python
from fastapi import BackgroundTasks

@app.post("/predict-async")
async def predict_async(
    req: PredictRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Return immediately, process in background
    background_tasks.add_task(predict_and_save, req, db)
    return {"status": "processing"}
```

## Deployment Checklist

Before deploying to production:

- [ ] All tests passing: `pytest`
- [ ] Code linted: `flake8`, `pylint`
- [ ] Security check: `bandit` for vulnerabilities
- [ ] Environment variables set correctly
- [ ] Database backups configured
- [ ] Logging configured (not just stdout)
- [ ] Error handling covers edge cases
- [ ] API documentation up-to-date
- [ ] Load testing passed
- [ ] SSL/TLS enabled
- [ ] CORS configured properly

## Documentation Standards

### Docstring Format

```python
def predict(features: dict) -> dict:
    """
    Predict crop recommendation based on environmental features.
    
    Args:
        features: Dictionary with keys [N, P, K, temperature, humidity, ph, rainfall]
    
    Returns:
        Dictionary with 'predictions' list containing crop and probability
    
    Raises:
        ValueError: If features missing required keys
        FileNotFoundError: If model file not found
    
    Example:
        >>> result = predict({"N": 50, "P": 40, ...})
        >>> result["predictions"][0]["crop"]
        'Rice'
    """
    pass
```

### Endpoint Documentation

```python
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    """
    Generate crop recommendations.
    
    Accepts either farm_id (queries latest reading) or explicit features dict.
    Uses trained RandomForest model to predict top crops.
    
    - **farm_id** (optional): Integer ID of farm (queries latest sensor reading)
    - **features** (optional): Dict with N, P, K, temp, humidity, ph, rainfall
    
    Returns top 5 crop predictions with probabilities.
    """
    pass
```

## Troubleshooting Common Issues

### Import Errors

```
ModuleNotFoundError: No module named 'app'
```

**Solution**: Ensure you're in correct directory:
```bash
cd services/api
python -c "from app.main import app"
```

### Database Connection Errors

```
psycopg2.OperationalError: could not connect to server
```

**Solution**: Check database is running:
```bash
docker compose logs db | grep "ready"
docker compose restart db
```

### Pydantic Validation Errors

```
ValidationError: value is not a valid integer
```

**Solution**: Type hints matter in Pydantic v2:
```python
class MyModel(BaseModel):
    count: int  # Not str or float
```

### Model Loading Failures

```
FileNotFoundError: ml/models/crop_rf.joblib
```

**Solution**: Train or generate model:
```bash
python ml/train.py
# or
python ml/gen_dummy_model.py
```

## Contributing Guidelines

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Write tests** for new code
3. **Follow style guide**: Run `black` and `flake8`
4. **Update documentation**: README, API docs, this guide
5. **Commit with clear messages**: `git commit -m "feat: add XYZ endpoint"`
6. **Submit PR** with description of changes

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy ORM Guide](https://docs.sqlalchemy.org)
- [Pydantic Documentation](https://pydantic-settings.readthedocs.io)
- [Streamlit Documentation](https://docs.streamlit.io)
- [TimescaleDB Documentation](https://docs.timescale.com)
- [PostgreSQL Documentation](https://www.postgresql.org/docs)

---

**Last Updated**: November 2025
