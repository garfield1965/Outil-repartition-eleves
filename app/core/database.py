"""
Mise en place du moteur SQLAlchemy et de la session.
Base SQLite mono-fichier : aucune installation de serveur de BD requise,
ce qui correspond à la contrainte "application autonome".
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},  # nécessaire avec FastAPI/uvicorn
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """Dépendance FastAPI : fournit une session et la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crée les tables si elles n'existent pas encore."""
    from app.core import models  # noqa: F401 (assure l'enregistrement des modèles)
    Base.metadata.create_all(bind=engine)
