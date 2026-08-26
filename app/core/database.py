from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
from typing import Generator

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Pre-ping para evitar conexiones muertas
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # logs SQL en dev
    # future=True,  # opcional si querés semántica 2.0 estricta
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()



def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
