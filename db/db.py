from db import models
from sqlmodel import SQLModel, create_engine
from dotenv import dotenv_values

config = dotenv_values()

POSTGRES_SQLALCHEMY_URI = f'postgresql://{config["DBUSER"]}:{config["DBPASS"]}@{config["DBHOST"]}.postgres.database.azure.com:5432/{config["DBNAME"]}'

engine = create_engine(POSTGRES_SQLALCHEMY_URI)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
