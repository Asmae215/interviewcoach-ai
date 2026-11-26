import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "interviewcoach.db"


def database_url() -> str:
    """SQLite en local ; en production, la base PostgreSQL (Neon) donnée par DATABASE_URL.

    Neon fournit une adresse « postgresql://… » : on précise le pilote psycopg (version 3).
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{DB_PATH}"
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping : Neon met la base en veille, une connexion ancienne peut être fermée
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Ouvre une session de base de données et la ferme à la fin de la requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns() -> None:
    """Mini-migration : ajoute aux tables existantes les colonnes créées après coup.

    create_all() crée les tables manquantes mais ne modifie pas une table qui existe déjà.
    """
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in existing:
                column_type = column.type.compile(engine.dialect)
                with engine.begin() as connection:
                    connection.execute(
                        text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}")
                    )
