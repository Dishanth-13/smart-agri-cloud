from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReadingIn(BaseModel):
    sensor_id: Optional[str] = None
    farm_id: Optional[int] = None
    ts: Optional[datetime] = Field(default=None)
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    ph: Optional[float] = None
    rainfall: Optional[float] = None
    n: Optional[int] = None
    p: Optional[int] = None
    k: Optional[int] = None

class PredictRequest(BaseModel):
    farm_id: Optional[int] = None
    features: Optional[dict] = None

class PredictResponse(BaseModel):
    predictions: list

class Health(BaseModel):
    status: str
