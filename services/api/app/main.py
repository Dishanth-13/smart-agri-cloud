from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app import models, crud
from app.schemas import ReadingIn, PredictRequest, PredictResponse, Health, ModelIn, ModelOut
from app.config import settings
import joblib
import numpy as np

app = FastAPI(title='smart-agri-api')

# create tables metadata (note: in production use migrations)
models.Base.metadata.create_all(bind=engine)

# ensure models table exists with desired columns (id,name,path,version,accuracy,model_metadata,active,created_at)
with engine.connect() as conn:
    conn.execute(text('''
    CREATE TABLE IF NOT EXISTS models (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        path TEXT NOT NULL,
        version TEXT,
        accuracy DOUBLE PRECISION,
        model_metadata JSONB,
        active BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    '''))

    # ensure columns exist (Postgres supports IF NOT EXISTS in ADD COLUMN from newer versions)
    try:
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS version TEXT;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS accuracy DOUBLE PRECISION;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS model_metadata JSONB;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now();"))
    except Exception:
        pass
    conn.commit()


# dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get('/health', response_model=Health)
def health():
    return {'status': 'ok'}

@app.post('/ingest')
def ingest(reading: ReadingIn, db: Session = Depends(get_db)):
    r = crud.create_reading(db, reading)
    return JSONResponse({"id": r.id, "ts": str(r.ts)})

@app.post('/models/register', response_model=ModelOut)
def register_model(model_in: ModelIn, db: Session = Depends(get_db)):
    m = crud.register_model(db, name=model_in.name, path=model_in.path, version=model_in.version, accuracy=model_in.accuracy, metadata=None if model_in.metadata is None else str(model_in.metadata), activate=bool(model_in.activate))
    return {
        'id': m.id,
        'name': m.name,
        'path': m.path,
        'version': m.version,
        'accuracy': m.accuracy,
        'metadata': None if not m.model_metadata else m.model_metadata,
        'active': 1 if m.active else 0,
        'created_at': m.created_at
    }

@app.get('/models/latest', response_model=ModelOut)
def get_latest_model(db: Session = Depends(get_db)):
    m = crud.get_active_model(db)
    if not m:
        raise HTTPException(status_code=404, detail='No active model registered')
    return {
        'id': m.id,
        'name': m.name,
        'path': m.path,
        'version': m.version,
        'accuracy': m.accuracy,
        'metadata': None if not m.model_metadata else m.model_metadata,
        'active': 1 if m.active else 0,
        'created_at': m.created_at
    }

@app.get('/models/list')
def list_all_models(db: Session = Depends(get_db)):
    """List all registered models ordered by creation date (newest first)"""
    models_list = crud.list_models(db, limit=100)
    return [
        {
            'id': m.id,
            'name': m.name,
            'path': m.path,
            'version': m.version,
            'accuracy': m.accuracy,
            'metadata': None if not m.model_metadata else m.model_metadata,
            'active': bool(m.active),
            'created_at': m.created_at
        }
        for m in models_list
    ]

@app.post('/predict', response_model=PredictResponse)
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    # resolve features
    if req.features:
        feats = req.features
    elif req.farm_id:
        r = crud.get_latest_reading_for_farm(db, req.farm_id)
        if not r:
            raise HTTPException(status_code=404, detail='No readings for farm')
        feats = {
            'N': r.n or 0,
            'P': r.p or 0,
            'K': r.k or 0,
            'temperature': r.temperature or 0.0,
            'humidity': r.humidity or 0.0,
            'ph': r.ph or 0.0,
            'rainfall': r.rainfall or 0.0
        }
    else:
        raise HTTPException(status_code=400, detail='Provide features or farm_id')

    # load model: prefer DB-registered active model, else fall back to configured model path
    try:
        model = None
        mrec = crud.get_active_model(db)
        tried_paths = []
        if mrec and mrec.path:
            tried_paths.append(mrec.path)
            try:
                model = joblib.load(mrec.path)
            except Exception:
                model = None
        if model is None:
            # fallback to configured model path
            tried_paths.append(settings.model_path)
            try:
                model = joblib.load(settings.model_path)
            except Exception:
                model = None
        if model is None:
            # Demo mode: return placeholder predictions if model doesn't exist
            preds = [
                {'crop': 'Rice', 'probability': 0.45},
                {'crop': 'Maize', 'probability': 0.35},
                {'crop': 'Wheat', 'probability': 0.20}
            ]
            return {'predictions': preds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to load model: {e}')

    # order features to match training: N,P,K,temp,humidity,ph,rainfall
    order = ['N','P','K','temperature','humidity','ph','rainfall']
    x = np.array([[feats.get(k, 0) for k in order]])

    try:
        # Determine top_k (default to 5 if not provided)
        top_k = int(req.top_k) if getattr(req, 'top_k', None) else 5
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(x)[0]
            classes = model.classes_
            pairs = sorted(zip(classes, probs), key=lambda x: -x[1])[:top_k]
            preds = [{'crop': str(c), 'probability': float(p)} for c,p in pairs]
        else:
            pred = model.predict(x)[0]
            preds = [{'crop': str(pred), 'probability': 1.0}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Prediction failed: {e}')

    return {'predictions': preds}
