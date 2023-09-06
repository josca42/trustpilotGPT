import pandas as pd
from copy import deepcopy
import openai
import json
from jinja2 import Template
from json.decoder import JSONDecodeError
from datetime import datetime
from assistant.config import CATEGORY_INT2STR
from assistant.db import crud


def sql(queries, metadata, gpt) -> str:
    # Extract filters from metadata
    start_date = metadata.pop("start_date")
    end_date = metadata.pop("end_date")
    filters_stmt = " AND ".join(
        [f"{k} in {tuple(v)}" for k, v in metadata.items() if v]
    )

    queries_result = []
    for query in queries:
        # Get ChatGPT to create sql query
        chatgpt_query = SQL_QUERY_PROMPT.render(
            question=query,
            filters=filters_stmt,
            start_date=start_date,
            end_date=end_date,
        )
        sql_query = gpt.completion(
            model="gpt-3.5-turbo",
            messages=[dict(role="user", content=chatgpt_query)],
            stop="SQLResult:",
            write_to_streamlit=False,
            name="SQL query",
            kind="llm",
        )
        sql_query = sql_query.strip(' "\n')

        # Execute sql query and return result
        df = crud.exec_sql(sql_query)
        queries_result.append(
            dict(
                SQLQuery=sql_query,
                SQLResult=df.head(20).astype(str).to_dict("records"),
            )
        )
    return queries_result


def data(queries, metadata):
    params = dict(
        cols=["company", "category", "content"],
        limit=int(150 / len(queries)),
        _in=dict(company=metadata["companies"], category=metadata["categories"]),
        start_date=metadata["start_date"],
        end_date=metadata["end_date"],
    )
    df = []
    for query in queries:
        df_t = crud.review.where(similarity_query=query, **params)
        df_t["similarity_query"] = query
        df.append(df_t)
    df = pd.concat(df)
    if not df.empty:
        df["category"] = df["category"].apply(lambda x: CATEGORY_INT2STR[x])
    return df


###   Prompts   ###
SQL_QUERY_PROMPT = Template(
    """Given an input question, first create a syntactically correct PostgreSQL query to run, then look at the results of the query and return the answer.

Never query for all the columns from a specific table, only ask for the few relevant columns given the question.

Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist.

Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here"

Use the table review, where each row is a review along with the review rating and category. Each company has multiple reviews. The table review has the following columns:

rating: integer. The rating of the review on a scale from 1 to 5. 
timestamp: datetime. The timestamp of the review.
category: Review category.
company: The company that the review is about.

{% if filters -%}
Add the following filters to the query:
{{ filters}}

{% endif -%}

{% if start_date and not end_date -%}
Add the following date filter to the query:
timestamp >= '{{ start_date }}'

{% elif end_date and not start_date -%}
Add the following date filter to the query:
timestamp <= '{{ end_date }}'

{% elif start_date and end_date -%}
Add the following date filter to the query:
timestamp BETWEEN '{{ start_date }}' AND '{{ end_date }}'

{% endif -%}

Question: {{ question}}
SQLQuery:"""
)
