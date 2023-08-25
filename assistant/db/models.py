from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, DateTime, Boolean, Column, Integer, String
from sqlalchemy import Column
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from typing import Any
from pydantic import validator
import pandas as pd
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column


###   Data tables   ###
class Company(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, index=True)
    name: str
    homepage: str
    stars: float
    trust_score: float
    n_reviews: int
    country: str
    embedding: Optional[list[float]] = Field(sa_column=Column(Vector(1536)))


class Review(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    company_name: str
    timestamp: datetime = Field(index=True)
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    content: Optional[str] = ""
    rating: int
    likes: Optional[int] = None
    category: Optional[str] = ""
    embedding: Optional[list[float]] = Field(sa_column=Column(Vector(1536)))
