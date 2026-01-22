"""
Script to set up the database and create tables
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models import Base
from database import engine

load_dotenv()

def setup_database():
    """Create database tables and enable PostGIS"""
    print("Setting up database...")
    
    # Enable PostGIS extension
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
        print("✓ PostGIS extension enabled")
    except Exception as e:
        print(f"Warning: Could not enable PostGIS: {e}")
        print("Make sure PostGIS is installed: CREATE EXTENSION postgis;")
    
    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise
    
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()
