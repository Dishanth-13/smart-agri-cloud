from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models
from app.schemas import ReadingIn
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_reading(db: Session, reading: ReadingIn):
    r = models.Reading(
        sensor_id=reading.sensor_id,
        farm_id=reading.farm_id,
        temperature=reading.temperature,
        humidity=reading.humidity,
        ph=reading.ph,
        rainfall=reading.rainfall,
        n=reading.n,
        p=reading.p,
        k=reading.k
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

def create_readings_bulk(db: Session, readings: list):
    """
    Bulk insert readings with batch processing
    
    Args:
        db: Database session
        readings: List of ReadingIn objects
    
    Returns:
        Tuple of (successful_count, failed_count, errors)
    """
    successful = 0
    failed = 0
    errors = []
    batch_size = 500
    
    try:
        for i in range(0, len(readings), batch_size):
            batch = readings[i:i+batch_size]
            try:
                for reading in batch:
                    r = models.Reading(
                        sensor_id=reading.sensor_id,
                        farm_id=reading.farm_id,
                        temperature=reading.temperature,
                        humidity=reading.humidity,
                        ph=reading.ph,
                        rainfall=reading.rainfall,
                        n=reading.n,
                        p=reading.p,
                        k=reading.k
                    )
                    db.add(r)
                
                db.commit()
                successful += len(batch)
            except Exception as e:
                db.rollback()
                failed += len(batch)
                errors.append({
                    'batch': i // batch_size,
                    'error': str(e),
                    'rows_affected': len(batch)
                })
                logger.error(f"Batch {i//batch_size} failed: {e}")
    except Exception as e:
        logger.error(f"Bulk insert failed: {e}")
        errors.append({'error': str(e)})
    
    return successful, failed, errors

def get_data_statistics(db: Session):
    """
    Get aggregate statistics about readings
    """
    try:
        total = db.query(func.count(models.Reading.id)).scalar() or 0
        unique_farms = db.query(func.count(func.distinct(models.Reading.farm_id))).scalar() or 0
        unique_sensors = db.query(func.count(func.distinct(models.Reading.sensor_id))).scalar() or 0
        
        # Date range
        min_date = db.query(func.min(models.Reading.ts)).scalar()
        max_date = db.query(func.max(models.Reading.ts)).scalar()
        
        # Temperature stats
        temp_min = db.query(func.min(models.Reading.temperature)).scalar()
        temp_max = db.query(func.max(models.Reading.temperature)).scalar()
        temp_avg = db.query(func.avg(models.Reading.temperature)).scalar()
        
        # Humidity stats
        humidity_min = db.query(func.min(models.Reading.humidity)).scalar()
        humidity_max = db.query(func.max(models.Reading.humidity)).scalar()
        humidity_avg = db.query(func.avg(models.Reading.humidity)).scalar()
        
        return {
            'total_readings': int(total),
            'unique_farms': int(unique_farms),
            'unique_sensors': int(unique_sensors),
            'date_range': {
                'min': str(min_date) if min_date else None,
                'max': str(max_date) if max_date else None
            },
            'temp_stats': {
                'min': float(temp_min) if temp_min else None,
                'max': float(temp_max) if temp_max else None,
                'avg': float(temp_avg) if temp_avg else None
            },
            'humidity_stats': {
                'min': float(humidity_min) if humidity_min else None,
                'max': float(humidity_max) if humidity_max else None,
                'avg': float(humidity_avg) if humidity_avg else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {
            'total_readings': 0,
            'unique_farms': 0,
            'unique_sensors': 0,
            'date_range': {'min': None, 'max': None},
            'temp_stats': {'min': None, 'max': None, 'avg': None},
            'humidity_stats': {'min': None, 'max': None, 'avg': None}
        }

def get_readings_filtered(db: Session, farm_id=None, sensor_id=None, start_date=None, end_date=None, temp_min=None, temp_max=None, limit=100):
    """
    Get filtered readings
    """
    query = db.query(models.Reading)
    
    if farm_id:
        query = query.filter(models.Reading.farm_id == farm_id)
    if sensor_id:
        query = query.filter(models.Reading.sensor_id == sensor_id)
    if start_date:
        query = query.filter(models.Reading.ts >= start_date)
    if end_date:
        query = query.filter(models.Reading.ts <= end_date)
    if temp_min is not None:
        query = query.filter(models.Reading.temperature >= temp_min)
    if temp_max is not None:
        query = query.filter(models.Reading.temperature <= temp_max)
    
    return query.order_by(models.Reading.ts.desc()).limit(limit).all()

def truncate_readings(db: Session):
    """
    Delete all readings
    """
    try:
        db.query(models.Reading).delete()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error truncating readings: {e}")
        return False

def get_latest_reading_for_farm(db: Session, farm_id: int):
    return db.query(models.Reading).filter(models.Reading.farm_id==farm_id).order_by(models.Reading.ts.desc()).first()

# Model CRUD

def register_model(db: Session, name: str, path: str, version: str=None, accuracy: float=None, metadata: str=None, activate: bool=False):
    m = models.ModelRecord(name=name, path=path, version=version, accuracy=accuracy, model_metadata=metadata, active=activate)
    if activate:
        # deactivate others
        db.query(models.ModelRecord).update({models.ModelRecord.active: False})
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def get_active_model(db: Session):
    return db.query(models.ModelRecord).filter(models.ModelRecord.active==True).order_by(models.ModelRecord.created_at.desc()).first()


def list_models(db: Session, limit: int=10):
    return db.query(models.ModelRecord).order_by(models.ModelRecord.created_at.desc()).limit(limit).all()

