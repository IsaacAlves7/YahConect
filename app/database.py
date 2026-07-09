"""
Camada de conexão com o banco de dados (SQLAlchemy).
Funciona com SQLite (default, ótimo para dev/teste) ou PostgreSQL (produção),
bastando trocar a variável de ambiente DATABASE_URL.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def init_db() -> None:
    """Cria todas as tabelas caso ainda não existam."""
    from app import models  # noqa: F401  (garante que os modelos sejam registrados)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    """Context manager para uso fora do FastAPI (scripts, ETL)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """Dependency do FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
