from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models, crud
from app.schemas import ReadingIn, PredictRequest, PredictResponse, Health
from app.config import settings
import joblib
import numpy as np

# create tables metadata (note: in production use migrations)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title='smart-agri-api')

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

    # load model (optional for demo; return placeholder if missing)
    try:
        model = joblib.load(settings.model_path)
    except FileNotFoundError:
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
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(x)[0]
            classes = model.classes_
            pairs = sorted(zip(classes, probs), key=lambda x: -x[1])[:5]
            preds = [{'crop': str(c), 'probability': float(p)} for c,p in pairs]
        else:
            pred = model.predict(x)[0]
            preds = [{'crop': str(pred), 'probability': 1.0}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Prediction failed: {e}')

    return {'predictions': preds}
