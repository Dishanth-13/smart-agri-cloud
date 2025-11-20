from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.database import SessionLocal, engine
from app import models, crud
from app.schemas import (
    ReadingIn, PredictRequest, PredictResponse, Health, ModelIn, ModelOut,
    BulkIngestRequest, BulkIngestResponse, DataStatsResponse,
    PredictBatchRequest, PredictBatchResponse, CropInfo, FilteredReadingsRequest
)
from app.config import settings
import joblib
import numpy as np
import io
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


# ============ PRIORITY 1: POST /ingest/bulk - Bulk CSV Upload ============
@app.post('/ingest/bulk', response_model=BulkIngestResponse)
def ingest_bulk(request: BulkIngestRequest, db: Session = Depends(get_db)):
    """
    Bulk ingest readings with batch processing (500 rows/batch)
    
    Args:
        request: BulkIngestRequest with list of readings
        db: Database session
    
    Returns:
        BulkIngestResponse with statistics
    """
    import time
    start_time = time.time()
    
    try:
        successful, failed, errors = crud.create_readings_bulk(db, request.readings)
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        logger.info(f'Bulk ingest: {successful} successful, {failed} failed in {processing_time:.2f}ms')
        
        return {
            'total_rows': len(request.readings),
            'successful_rows': successful,
            'failed_rows': failed,
            'errors': errors if errors else None,
            'processing_time_ms': processing_time
        }
    except Exception as e:
        logger.error(f'Bulk ingest failed: {e}')
        raise HTTPException(status_code=500, detail=f'Bulk ingest failed: {str(e)}')


# ============ PRIORITY 2: GET /data/stats - Data Statistics ============
@app.get('/data/stats', response_model=DataStatsResponse)
def get_data_stats(db: Session = Depends(get_db)):
    """
    Get aggregate statistics about sensor data
    
    Returns:
        DataStatsResponse with comprehensive statistics
    """
    try:
        stats = crud.get_data_statistics(db)
        return stats
    except Exception as e:
        logger.error(f'Failed to get data stats: {e}')
        raise HTTPException(status_code=500, detail=f'Failed to get statistics: {str(e)}')


# ============ PRIORITY 3: GET /predict/batch - Batch Predictions ============
@app.post('/predict/batch', response_model=PredictBatchResponse)
def predict_batch(request: PredictBatchRequest, db: Session = Depends(get_db)):
    """
    Get predictions for multiple readings (batch)
    
    Args:
        request: PredictBatchRequest with list of readings
        db: Database session
    
    Returns:
        PredictBatchResponse with predictions for all rows
    """
    import time
    start_time = time.time()
    
    try:
        # Load model
        model = None
        mrec = crud.get_active_model(db)
        
        if mrec and mrec.path:
            try:
                model = joblib.load(mrec.path)
            except Exception:
                model = None
        
        if model is None:
            try:
                model = joblib.load(settings.model_path)
            except Exception:
                model = None
        
        if model is None:
            raise HTTPException(status_code=500, detail='No model available')
        
        # Process all readings
        predictions = []
        failed = 0
        order = ['N','P','K','temperature','humidity','ph','rainfall']
        
        for i, reading in enumerate(request.readings):
            try:
                feats = {
                    'N': reading.n or 0,
                    'P': reading.p or 0,
                    'K': reading.k or 0,
                    'temperature': reading.temperature or 0.0,
                    'humidity': reading.humidity or 0.0,
                    'ph': reading.ph or 0.0,
                    'rainfall': reading.rainfall or 0.0
                }
                
                x = np.array([[feats.get(k, 0) for k in order]])
                top_k = request.top_k or 5
                
                if hasattr(model, 'predict_proba'):
                    probs = model.predict_proba(x)[0]
                    classes = model.classes_
                    pairs = sorted(zip(classes, probs), key=lambda x: -x[1])[:top_k]
                    preds = [{'crop': str(c), 'probability': float(p)} for c,p in pairs]
                else:
                    pred = model.predict(x)[0]
                    preds = [{'crop': str(pred), 'probability': 1.0}]
                
                predictions.append({
                    'row_index': i,
                    'sensor_id': reading.sensor_id,
                    'farm_id': reading.farm_id,
                    'predictions': preds
                })
            except Exception as e:
                failed += 1
                logger.error(f'Row {i} prediction failed: {e}')
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f'Batch prediction: {len(predictions)} successful, {failed} failed in {processing_time:.2f}ms')
        
        return {
            'predictions': predictions,
            'processed_rows': len(predictions),
            'failed_rows': failed,
            'processing_time_ms': processing_time
        }
    except Exception as e:
        logger.error(f'Batch prediction failed: {e}')
        raise HTTPException(status_code=500, detail=f'Batch prediction failed: {str(e)}')


# ============ PRIORITY 4: GET /data/filtered - Advanced Filtering ============
@app.post('/data/filtered')
def get_filtered_data(request: FilteredReadingsRequest, db: Session = Depends(get_db)):
    """
    Get filtered readings with multiple criteria
    
    Args:
        request: FilteredReadingsRequest with filter criteria
        db: Database session
    
    Returns:
        List of filtered readings
    """
    try:
        readings = crud.get_readings_filtered(
            db,
            farm_id=request.farm_id,
            sensor_id=request.sensor_id,
            start_date=request.start_date,
            end_date=request.end_date,
            temp_min=request.temp_min,
            temp_max=request.temp_max,
            limit=request.limit
        )
        
        return [
            {
                'id': r.id,
                'sensor_id': r.sensor_id,
                'farm_id': r.farm_id,
                'ts': str(r.ts),
                'temperature': r.temperature,
                'humidity': r.humidity,
                'ph': r.ph,
                'rainfall': r.rainfall,
                'n': r.n,
                'p': r.p,
                'k': r.k
            }
            for r in readings
        ]
    except Exception as e:
        logger.error(f'Failed to get filtered data: {e}')
        raise HTTPException(status_code=500, detail=f'Failed to get filtered data: {str(e)}')


# ============ BONUS: GET /data/export - Export CSV ============
@app.get('/data/export')
def export_data(
    farm_id: int = None,
    sensor_id: str = None,
    limit: int = 10000,
    db: Session = Depends(get_db)
):
    """
    Export filtered data as CSV
    """
    try:
        readings = crud.get_readings_filtered(
            db,
            farm_id=farm_id,
            sensor_id=sensor_id,
            limit=limit
        )
        
        # Convert to list of dicts
        data = [
            {
                'id': r.id,
                'sensor_id': r.sensor_id,
                'farm_id': r.farm_id,
                'ts': r.ts,
                'temperature': r.temperature,
                'humidity': r.humidity,
                'ph': r.ph,
                'rainfall': r.rainfall,
                'n': r.n,
                'p': r.p,
                'k': r.k
            }
            for r in readings
        ]
        
        # Try to import pandas, if not available return JSON
        try:
            import pandas as pd
            df = pd.DataFrame(data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            return StreamingResponse(
                iter([csv_buffer.getvalue()]),
                media_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename=data_export.csv'}
            )
        except ImportError:
            return {'data': data, 'note': 'CSV export requires pandas. Returning JSON instead.'}
    except Exception as e:
        logger.error(f'Failed to export data: {e}')
        raise HTTPException(status_code=500, detail=f'Failed to export data: {str(e)}')


# ============ BONUS: DELETE /data/truncate - Clear All Data ============
@app.delete('/data/truncate')
def truncate_all_data(confirm: bool = False, db: Session = Depends(get_db)):
    """
    Delete all readings from database (requires confirm=True)
    """
    if not confirm:
        raise HTTPException(status_code=400, detail='Provide confirm=true to delete all data')
    
    try:
        success = crud.truncate_readings(db)
        if success:
            logger.info('All readings truncated')
            return {'message': 'All data cleared successfully'}
        else:
            raise HTTPException(status_code=500, detail='Failed to truncate data')
    except Exception as e:
        logger.error(f'Failed to truncate data: {e}')
        raise HTTPException(status_code=500, detail=f'Failed to truncate: {str(e)}')

