from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/ct_properties")
    
    class Config:
        env_file = ".env"

settings = Settings()

engine = create_engine(
    settings.database_url,
    pool_size=10,  # Support parallel workers
    max_overflow=20,  # Allow additional connections during peak load
    pool_pre_ping=True,  # Verify connections before using
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
