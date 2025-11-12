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
    top_k: Optional[int] = 5

class PredictResponse(BaseModel):
    predictions: list

class ModelIn(BaseModel):
    name: str
    path: str
    version: Optional[str] = None
    accuracy: Optional[float] = None
    metadata: Optional[dict] = None
    activate: Optional[bool] = False

class ModelOut(BaseModel):
    id: int
    name: str
    path: str
    version: Optional[str] = None
    accuracy: Optional[float] = None
    metadata: Optional[dict] = None
    active: Optional[int] = 0
    created_at: Optional[datetime] = None

class Health(BaseModel):
    status: str
