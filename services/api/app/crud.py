from sqlalchemy.orm import Session
from app import models
from app.schemas import ReadingIn

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
