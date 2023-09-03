import ast
import pandas as pd
from jinja2 import Template
from assistant.llm import num_tokens_from_string
import json

MAX_TOKENS = 5000


def review_text(query_data, question, gpt):
    query, df = query_data["query"], query_data["data"]
    df_s = get_representative_sample(df, max_tokens=MAX_TOKENS)
    reviews = []
    for group, df_g in df_s.groupby(["company", "category"]):
        reviews.append(
            dict(company=group[0], category=group[1], reviews=df_g["content"].to_list())
        )
    reviews_json_str = json.dumps(reviews, ensure_ascii=False)
    user_msg = REVIEW_ANALYSIS_USER_QUERY.render(
        reviews=reviews_json_str, question=question
    )
    messages = [dict(role="system", content=REVIEW_ANALYSIS_SYS_MSG)] + [
        dict(role="user", content=user_msg)
    ]
    analysis_txt = gpt.completion(messages=messages, model="gpt-4")
    return analysis_txt


def review_data(query_data, question, gpt):
    query, df = query_data["query"], query_data["data"]


# t = exec(code)

# df = pd.read_json(action_data["data"])
# code = action_data["code"]

# # Use ast to execute the code and extract the variable `fig`
# node = ast.parse(code)
# local_namespace = {"df": df}
# exec(compile(node, "<ast>", "exec"), local_namespace)
# fig = local_namespace.get("fig")
# return dcc.Graph(figure=fig, style=style)
#
#
#
#
#


def sql_query(query, question, gpt):
    user_query = SQL_USER_QUERY.render(
        sql_query=query["query"], sql_result=query["result"], question=question
    )
    messages = [dict(role="system", content=SQL_SYS_MSG)] + [
        dict(role="user", content=user_query)
    ]
    analysis = gpt.completion(messages=messages, model="gpt-4")
    return analysis.message.content


def get_representative_sample(df, max_tokens):
    # FIXME: Add take top n reviews sorted by similarity distance if similarity_query is not None
    avg_tokens_pr_review = (
        df["content"]
        .sample(300 if len(df) > 300 else len(df))
        .apply(lambda x: num_tokens_from_string(x, model="gpt-4"))
        .mean()
    )
    n_reviews = int(max_tokens / avg_tokens_pr_review)
    df["combined"] = list(zip(df["category"], df["company"]))
    weight = df["combined"].value_counts(normalize=True)
    df["combined_weight"] = df["combined"].apply(lambda x: weight[x])
    df_sample = df.sample(n_reviews, weights=df["combined_weight"])
    return df_sample


def descr_df(df: pd.DataFrame) -> str:
    summary = ""
    summary += f"The dataframe has {df.shape[0]} rows and {df.shape[1]} columns.\n"
    summary += "\nColumn details:\n"
    for col in df.columns:
        summary += f"- {col}: {df[col].dtype} (Non-null: {df[col].notna().sum()} of {df.shape[0]})\n"
    return summary


###   Prompts   ###

SQL_SYS_MSG = """As a skilled analyst specializing in customer reviews, your task is to answer questions about customer reviews using a provided SQL query and corresponding SQL result. The format of a user question is therefore as follows:

SQLQuery: "SQL query string"
SQLResult: "SQL query result"
Question: "User question that should be answered by the SQL query and SQL result" 

Always answer in the same language as the question."""

SQL_USER_QUERY = Template(
    """SQLQuery: {{ sql_query }}
SQLResult: {{ sql_result }}
Question: {{ question }}"""
)


REVIEW_ANALYSIS_SYS_MSG = """As a skilled analyst specializing in customer review data, your task is to answer questions by analysing the provided reviews. The format of a user question is therefore as follows:

Reviews:
[
    {
        company: "The name of the company the reviews are about",
        category: "The category of the reviews",
        reviews: ["review string", "review string", ...],
        /* Each review string is the content of a unique review */
    },
    /* more reviews of similar or different company and/or category */

]
Question: User question

When responding, ensure to address the specific question asked, and focus on the patterns, trends, and insights derived from reviews. The response should be flexible and adaptable to various relevant and creative questions, emphasizing accuracy and relevance.
Always answer in the same language as the question.
"""

REVIEW_ANALYSIS_USER_QUERY = Template(
    """Reviews:
{{ reviews }}

Question: {{ question }}"""
)
