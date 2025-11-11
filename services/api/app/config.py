import os

class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@db:5432/smart_agri')
    model_path: str = os.getenv('MODEL_PATH', '/app/models/crop_rf.joblib')

settings = Settings()
