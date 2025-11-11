from sqlalchemy import Column, Integer, BigInteger, Text, TIMESTAMP, Float
from sqlalchemy.sql import func
from app.database import Base

class Reading(Base):
    __tablename__ = 'readings'
    id = Column(BigInteger, primary_key=True, index=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
    sensor_id = Column(Text)
    temperature = Column(Float)
    humidity = Column(Float)
    ph = Column(Float)
    rainfall = Column(Float)
    n = Column(Integer)
    p = Column(Integer)
    k = Column(Integer)
    farm_id = Column(Integer)

class Farm(Base):
    __tablename__ = 'farms'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    location = Column(Text)

class ModelRecord(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    path = Column(Text)
