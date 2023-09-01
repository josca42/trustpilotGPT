from assistant.db import crud
import pandas as pd
from jinja2 import Template
from assistant.llm import num_tokens_from_string
from .CONSTANTS import CATEGORY_INT2STR, CATEGORY_STR2INT
from .utils import str2date


MAX_TOKENS = 6000
COLS = [
    "content",
    "timestamp",
    "company",
    "category",
    "rating",
    "country",
]


def query_data(queries: list[dict], gpt) -> list[dict]:
    """
    parent_trace: Wandb parent logging execution of an LLM chain.
    """
    results = []
    for query in queries:
        data_query = query.pop("query", None)
        params = json_to_params(query)
        if data_query:
            df, sql_query = get_review_stats(params, data_query=data_query, gpt=gpt)
            results.append(
                dict(
                    SQLQuery=sql_query,
                    SQLResult=df.head(10).astype(str).to_dict("records"),
                    SQLResultDescription=descr_df(df),
                    data=df,
                )
            )
        else:
            df = get_review_data(params)
            results.append(
                dict(
                    review_query=data_query,
                    reviews=df["content"].tolist(),
                )
            )
    return results


def get_review_data(params: dict) -> pd.DataFrame:
    params.update({"cols": COLS, "limit": 100})
    df = crud.review.similarity_query(**params)
    if "category" in df.columns and not df.empty:
        df["category"] = df["category"].apply(lambda x: CATEGORY_INT2STR[x])
    return df


def get_review_stats(params: dict, data_query: str, gpt) -> pd.DataFrame:
    start_date = params.pop("start_date", None)
    end_date = params.pop("end_date", None)

    filters_stmt = " AND ".join(
        [
            f"{k} = {v}" if type(v) == int else f"{k} = '{v}'"
            for k, v in params["equals"].items()
        ]
    )

    chatgpt_query = SQL_QUERY_PROMPT.render(
        question=data_query,
        filters=filters_stmt,
        start_date=start_date,
        end_date=end_date,
    )
    sql_query = gpt.completion(
        model="gpt-3.5-turbo",
        messages=[dict(role="user", content=chatgpt_query)],
        stop="\nSQLResult:",
    ).message.content
    sql_query = sql_query.strip('"')
    df = crud.exec_sql(sql_query)
    return df, sql_query


def json_to_params(json_request: dict) -> dict:
    if not json_request:
        return {}

    equals = {}
    start_date, end_date, similarity_query = None, None, None
    for field, value in json_request.items():
        if value is None:
            continue
        elif field == "date_range":
            start_date = str2date(value["start"]) if "start" in value else None
            end_date = str2date(value["end"]) if "end" in value else None
        elif field == "company":
            company = crud.company.most_similar_name(
                similarity_query=value,
            )
            equals["company"] = company
        elif field == "category":
            cat, cat_type = crud.lookup.where(
                similarity_query=value,
                lookup_type="category",
            )
            equals["category"] = CATEGORY_STR2INT[cat]
        elif field == "similarity_query":
            similarity_query = value
        else:
            equals[field] = value

    params = dict(
        start_date=start_date,
        end_date=end_date,
        similarity_query=similarity_query,
        equals=equals,
    )
    return params


def get_representative_sample(df, max_tokens):
    # FIXME: Add take top n reviews sorted by similarity distance if similarity_query is not None
    avg_tokens_pr_review = (
        df["content"]
        .sample(300 if len(df) > 300 else len(df))
        .apply(lambda x: num_tokens_from_string(x, model="gpt-4"))
        .mean()
    )
    n_reviews = int(max_tokens / avg_tokens_pr_review)
    df["combined"] = list(zip(df["rating"], df["category"], df["company"]))
    weight = df["combined"].value_counts(normalize=True)
    df["combined_weight"] = df["combined"].apply(lambda x: weight[x])
    df_sample = df.sample(n_reviews, weights=df["combined_weight"])
    return df_sample


# def descr_df(df: pd.DataFrame) -> str:
#     summary = ""
#     summary += f"The dataframe has {df.shape[0]} rows and {df.shape[1]} columns.\n"
#     summary += "\nColumn details:\n"
#     for col in df.columns:
#         summary += f"- {col}: {df[col].dtype} (Non-null: {df[col].notna().sum()} of {df.shape[0]})\n"
#     return summary


###    Prompt templates    ###


SQL_QUERY_PROMPT = Template(
    """Given an input question, first create a syntactically correct PostgreSQL query to run, then look at the results of the query and return the answer.

Never query for all the columns from a specific table, only ask for the few relevant columns given the question.

Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist.

Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here"

Use the table review with the following columns:

rating: integer. The rating of the review on a scale from 1 to 5. 
timestamp: datetime. The timestamp of the review.
category: Review category.
company: The company that the review is about.
country: The country of the company. Possible values: 'DK', 'NO', 'SE', 'FO'.

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
