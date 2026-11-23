from sqlalchemy import inspect

from backend.database import Base, engine
import backend.models  # noqa: F401

Base.metadata.create_all(engine)
print(inspect(engine).get_table_names())
