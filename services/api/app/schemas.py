from pydantic import BaseModel, Field
from typing import Optional, List
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

class BulkIngestRequest(BaseModel):
    """Request schema for bulk data ingestion"""
    readings: List[ReadingIn]
    batch_size: Optional[int] = 500

class BulkIngestResponse(BaseModel):
    """Response schema for bulk ingestion"""
    total_rows: int
    successful_rows: int
    failed_rows: int
    errors: Optional[List[dict]] = None
    processing_time_ms: float

class DataStatsResponse(BaseModel):
    """Response schema for data statistics"""
    total_readings: int
    unique_farms: int
    unique_sensors: int
    date_range: dict
    temp_stats: dict
    humidity_stats: dict

class PredictBatchRequest(BaseModel):
    """Request schema for batch predictions"""
    readings: List[ReadingIn]
    top_k: Optional[int] = 5

class PredictBatchResponse(BaseModel):
    """Response schema for batch predictions"""
    predictions: List[dict]
    processed_rows: int
    failed_rows: int
    processing_time_ms: float

class CropInfo(BaseModel):
    """Crop information"""
    name: str
    optimal_temp_min: float
    optimal_temp_max: float
    optimal_humidity_min: float
    optimal_humidity_max: float
    optimal_ph_min: float
    optimal_ph_max: float

class FilteredReadingsRequest(BaseModel):
    """Request schema for filtered readings"""
    farm_id: Optional[int] = None
    sensor_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    limit: Optional[int] = 100

