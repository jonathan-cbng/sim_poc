import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sim.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy session.
    Override in tests via app.dependency_overrides[get_db] = custom_factory
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
