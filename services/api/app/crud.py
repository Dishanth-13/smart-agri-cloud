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
