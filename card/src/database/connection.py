import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import sys
from pathlib import Path

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.insert(0, str(project_root))

# Database configuration for Supabase
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:Potato6200$@db.nymjvnuyrwshnzbwmxim.supabase.co:5432/postgres"
)

# Create engine with UUID support for Supabase
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # For development
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before use
    connect_args={
        "sslmode": "require",  # Supabase requires SSL
        "options": "-c timezone=utc"  # Set timezone for consistency
    }
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_database_session():
    """Get a database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_db_session():
    """Get a database session (alternative method)"""
    return SessionLocal()

def test_connection():
    """Test Supabase database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Supabase database connection successful!")
            
            # Test if our tables exist
            table_check = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('patients', 'devices', 'sessions')
            """))
            tables = [row[0] for row in table_check.fetchall()]
            
            if tables:
                print(f"✅ Found tables: {', '.join(tables)}")
                
                # Check data count
                for table in tables:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.fetchone()[0]
                    print(f"📊 {table}: {count} records")
            else:
                print("⚠️ No expected tables found.")
            
            return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("Check your Supabase credentials and internet connection")
        return False

if __name__ == "__main__":
    print("Testing Supabase database connection...")
    test_connection()