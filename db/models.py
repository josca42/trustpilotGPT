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
class Bank(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, index=True)
    bank: str = Field(index=True)
    bank_category: str = Field(index=True)
    bank_central: str = Field(index=True)
    android_id: str
    ios_id: str
    homepage: str
    country: str


class Lookup(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    lookup_type: str
    type: str
    name: str
    embedding: list[float] = Field(sa_column=Column(Vector(768)))


class Review(SQLModel):
    id: str = Field(primary_key=True, index=True)
    timestamp: datetime = Field(index=True)
    content: Optional[str] = ""
    rating: int
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    source: str
    bank_id: int = Field(foreign_key="bank.id", index=True)
    country: str = Field(index=True)
    bank: str = Field(index=True)
    bank_category: str = Field(index=True)
    bank_central: str = Field(index=True)
    label: Optional[int] = -1
    labeller: Optional[int] = -1
    customer_label: Optional[int] = -1
    anonymized: Optional[bool] = False
    embedding: Optional[list[float]] = Field(sa_column=Column(Vector(768)))


class Bank_Review(Review, table=True):
    ...


class App_Review(Review, table=True):
    user_name: Optional[str]
    app_version: Optional[str]
    reply_content: Optional[str]
    reply_timestamp: Optional[datetime]
    os: str = Field(index=True)
    likes: Optional[int] = 0

    @validator("likes")
    def nan2zero(cls, v):
        if isinstance(v, float) and pd.isnan(v):
            return 0
        return v

    @validator("reply_timestamp")
    def NaT2None(cls, v):
        if pd.isna(v):
            return None
        return v

    @validator("content", pre=True)
    def None2empty_string(cls, v):
        return v or ""
