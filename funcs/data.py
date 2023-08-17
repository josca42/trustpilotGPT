from db import crud, exec_sql
import pandas as pd
import jinja2
from .CONSTANTS import CATEGORY_INT2STR, CATEGORY_STR2INT
from llm import num_tokens_from_string, gpt_completion

MAX_TOKENS = 6000
COLS = [
    "content",
    "rating",
    "label",
    "timestamp",
    "os",
    "app_version",
    "bank_id",
    "bank",
    "bank_category",
    "bank_central",
    "country",
]


def get_data(review_queries: list(dict)) -> pd.DataFrame:
    query_results = []
    for query in review_queries:
        retrieve = query.pop("retrieve", None)
        params = json_to_params(query)
        if retrieve == "statistics":
            df = get_review_stats(params)
        else:
            df = get_review_data(params)
            query_results.append(dict(query=query, data=df.to_dict("records")))
    return query_results


def get_review_data(params: dict) -> pd.DataFrame:
    source = params.pop("source")
    params.update({"cols": COLS, "limit": 100})
    df = (
        crud.app_review.where_api(**params)
        if source == "app"
        else crud.bank_review.where_api(**params)
    )
    if "label" in df.columns and not df.empty:
        df["category"] = df["label"].apply(lambda x: CATEGORY_INT2STR[source][x])
    return df


def get_review_stats(params: dict) -> pd.DataFrame:
    source = params.pop("source")
    table = "app_review" if source == "app" else "bank_review"
    start_date = params.pop("start_date", None)
    end_date = params.pop("end_date", None)

    filters_stmt = " AND ".join(
        [f"{k} = {v}" if type(v) == int else f"{k} = '{v}'" for k, v in params.items()]
    )

    chatgpt_query = SQL_QUERY_TEMPLATE.render(
        table=table,
        question=filters_stmt,
        filters=filters_stmt,
        start_date=start_date,
        end_date=end_date,
    )
    query_str = gpt_completion(
        messages=[dict(role="user", content=chatgpt_query)],
        stop="\nSQLResult:",
    )
    query_str = query_str.strip('"')
    df = exec_sql(query_str)
    return df, query_str


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
        elif field == "source":
            source = value
        elif field == "bank":
            bank, bank_type = crud.lookup.where(
                similarity_query=value, lookup_type="bank"
            )
            equals[bank_type] = bank
        elif field == "category":
            cat, cat_type = crud.lookup.where(
                similarity_query=value,
                lookup_type="category",
                type=json_request["source"],
            )
            equals["label"] = CATEGORY_STR2INT[cat_type][cat]
        elif field == "similarity_query":
            similarity_query = value
        else:
            equals[field] = value

    params = dict(
        source=source,
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
    df["combined"] = list(zip(df["rating"], df["category"], df["bank_central"]))
    weight = df["combined"].value_counts(normalize=True)
    df["combined_weight"] = df["combined"].apply(lambda x: weight[x])
    df_sample = df.sample(n_reviews, weights=df["combined_weight"])
    return df_sample


def str2date(date_str):
    try:
        return pd.to_datetime(date_str).date()
    except:
        return None


###    Prompt templates    ###
jinja_env = jinja2.Environment()

SQL_QUERY_PROMPT = """Given an input question, first create a syntactically correct PostgreSQL query to run, then look at the results of the query and return the answer.

Never query for all the columns from a specific table, only ask for the few relevant columns given the question.

Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist.

Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here"

Use the table {{ table }} with the following columns:

rating: integer. The rating of the review on a scale from 1 to 5. 
timestamp: datetime. The timestamp of the review.
{% if table == "app_review" -%} 
os: text. The operating system of the mobile device used to write the review. Possible values: 'android', 'ios'.
{% endif -%}
label: Review category.
bank: The bank that the review is about.
bank_central: The bank central of the bank.
country: The country of the bank. Possible values: 'DK', 'NO', 'SE', 'UK', 'NZ', 'FO'.

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

SQL_QUERY_TEMPLATE = jinja_env.from_string(SQL_QUERY_PROMPT)
