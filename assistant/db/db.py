from assistant.db import models
from sqlmodel import SQLModel, create_engine
from assistant.config import config

POSTGRES_SQLALCHEMY_URI = f'postgresql://{config["PGUSER"]}:{config["PGPASSWORD"]}@{config["PGHOST"]}:5432/{config["PGDATABASE"]}'

engine = create_engine(POSTGRES_SQLALCHEMY_URI)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
