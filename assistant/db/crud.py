from typing import Generic, Type, TypeVar, List, Tuple
from sqlmodel import SQLModel, Session, select, delete, update, and_, or_
from sqlalchemy.future import Engine
from sqlalchemy.dialects.postgresql import insert
from assistant.db import models
from assistant.db.db import engine
import pandas as pd
from llm import cohere_embed

ModelType = TypeVar("ModelType", bound=SQLModel)
EngineType = TypeVar("EngineType", bound=Engine)


class CRUDBase(Generic[ModelType, EngineType]):
    def __init__(self, model: Type[ModelType], engine: Type[EngineType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLModel class
        * `engine`: A sqlalchemy engine
        """
        self.model = model
        self.engine = engine

    def get(self, id) -> ModelType:
        with Session(self.engine) as session:
            return session.get(self.model, id)

    def get_table(self):
        with Session(self.engine) as session:
            stmt = select(self.model)
            result = session.exec(stmt).all()
        return pd.DataFrame([r.dict() for r in result])

    def get_multi(self, offset: int = 0, limit: int = 100) -> List[ModelType]:
        with Session(self.engine) as session:
            return session.exec(select(self.model).offset(offset).limit(limit)).all()

    def create(self, model_obj: ModelType) -> ModelType:
        with Session(self.engine) as session, session.begin():
            stmt = insert(self.model).values(**model_obj.dict(exclude_unset=True))
            session.exec(stmt)

    def upsert(self, model_obj: ModelType) -> ModelType:
        with Session(self.engine) as session, session.begin():
            stmt = (
                insert(self.model)
                .values(**model_obj.dict(exclude_unset=True))
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_=model_obj.dict(exclude_unset=True),
                )
            )
            session.exec(stmt)

    def update(self, model_obj: ModelType) -> ModelType:
        model_update = model_obj.dict(exclude_unset=True)
        with Session(self.engine) as session, session.begin():
            stmt = update(self.model).where(self.model.id == model_obj.id)
            session.exec(stmt.values(**model_update))

    def delete(self, id) -> None:
        with Session(self.engine) as session, session.begin():
            stmt = delete(self.model).where(self.model.id == id)
            session.exec(stmt)

    def where(self, equals: dict = {}, _in: dict = {}) -> List[ModelType]:
        with Session(self.engine) as session:
            stmt = select(self.model)
            if equals:
                stmt = stmt.where(
                    and_(*[getattr(self.model, k) == v for k, v in equals.items()])
                )
            if _in:
                stmt = stmt.where(
                    or_(*[getattr(models.Bank, k).in_(v) for k, v in _in.items()])
                )
            result = session.exec(stmt).all()
        return pd.DataFrame([r.dict() for r in result])


class CRUDBank(CRUDBase[models.Bank, Engine]):
    ...


class CRUDReview(CRUDBase[ModelType, EngineType]):
    def where(
        self, cols, start_date=None, end_date=None, equals: dict = {}, _in: dict = {}
    ) -> List[ModelType]:
        with Session(self.engine) as session:
            stmt = select(*[getattr(self.model, s) for s in cols])
            where_stmts = []
            os = equals.pop("os", None)
            rating = _in.pop("rating", None)
            source = _in.pop("source", None)
            if equals:
                where_stmts += [getattr(self.model, k) == v for k, v in equals.items()]
            if _in:
                where_stmts += [getattr(self.model, k).in_(v) for k, v in _in.items()]
            if where_stmts:
                stmt = stmt.where(or_(*where_stmts))

            if os:
                stmt = stmt.where(self.model.os == os)
            if rating:
                stmt = stmt.where(self.model.rating.in_(rating))
            if source:
                stmt = stmt.where(self.model.source.in_(source))

            if start_date and end_date:
                stmt = stmt.where(self.model.timestamp.between(start_date, end_date))
            elif start_date:
                stmt = stmt.where(self.model.timestamp >= start_date)
            elif end_date:
                stmt = stmt.where(self.model.timestamp <= end_date)
            else:
                pass

            result = session.exec(stmt).all()
        return pd.DataFrame.from_records(
            result,
            columns=cols,
        )

    def where_api(
        self,
        cols,
        start_date=None,
        end_date=None,
        equals: dict = {},
        similarity_query: str = None,
        limit=None,
        *args,
        **kwargs
    ) -> List[ModelType]:
        with Session(self.engine) as session:
            stmt = select(*[getattr(self.model, s) for s in cols])
            where_stmts = []
            if equals:
                where_stmts += [getattr(self.model, k) == v for k, v in equals.items()]
                stmt = stmt.where(and_(*where_stmts))

            if start_date and end_date:
                stmt = stmt.where(self.model.timestamp.between(start_date, end_date))
            elif start_date:
                stmt = stmt.where(self.model.timestamp >= start_date)
            elif end_date:
                stmt = stmt.where(self.model.timestamp <= end_date)
            else:
                pass

            if similarity_query:
                query_emb = cohere_embed(similarity_query)[0]
                stmt = stmt.order_by(self.model.embedding.l2_distance(query_emb))
            else:
                stmt.order_by(self.model.timestamp.desc())

            if limit:
                stmt = stmt.limit(limit)
            result = session.exec(stmt).all()
        return pd.DataFrame.from_records(
            result,
            columns=cols,
        )

    def check_if_bank_has_reviews(self, bank_id) -> List[ModelType]:
        with Session(self.engine) as session:
            stmt = select(self.model).where(self.model.bank_id == bank_id)
            return session.exec(stmt).first()


class CRUDBankReview(CRUDReview[models.Bank_Review, Engine]):
    ...


class CRUDAppReview(CRUDReview[models.App_Review, Engine]):
    ...


class CRUDLookup(CRUDBase[models.Lookup, Engine]):
    def where(
        self, similarity_query: str, lookup_type: str, type: str = None
    ) -> Tuple[str, str]:
        query_emb = cohere_embed(similarity_query)[0]
        with Session(self.engine) as session:
            stmt = select(self.model.name, self.model.type)
            stmt = (
                stmt.where(
                    and_(self.model.lookup_type == lookup_type, self.model.type == type)
                )
                if type
                else stmt.where(self.model.lookup_type == lookup_type)
            )
            stmt = stmt.order_by(self.model.embedding.l2_distance(query_emb)).limit(1)
            result = session.exec(stmt).first()
        return result


def exec_sql(sql):
    try:
        with Session(engine) as session:
            result = session.exec(sql).all()
        df = pd.DataFrame.from_records(
            result,
            columns=sql[sql.index("SELECT") + len("SELECT") : sql.index("FROM")]
            .strip()
            .split(", "),
        )
        return df
    except Exception as e:
        raise ValueError("Invalid SQL query")


app_review = CRUDAppReview(models.App_Review, engine)
bank_review = CRUDBankReview(models.Bank_Review, engine)
bank = CRUDBank(models.Bank, engine)
lookup = CRUDLookup(models.Lookup, engine)
