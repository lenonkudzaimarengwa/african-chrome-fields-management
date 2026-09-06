"""
Database Configuration and SQLAlchemy Setup
African Chrome Fields Management System
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chrome_user:chrome_password@localhost:5432/african_chrome_db"
)

logger.info(f"Connecting to database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")

# Create SQLAlchemy engine
# echo=True logs all SQL queries (useful for debugging, disable in production)
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False") == "True",
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all ORM models
Base = declarative_base()

# Dependency function for FastAPI routes
def get_db():
    """
    Dependency function to get database session in FastAPI routes.
    
    Usage in routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database (create all tables)
def init_db():
    """Create all database tables based on SQLAlchemy models"""
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables initialized")

# Health check function
async def check_database_connection():
    """
    Check if database is accessible.
    Useful for health check endpoints.
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
