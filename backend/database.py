from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "interviewcoach.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
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
