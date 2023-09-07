import ast
import pandas as pd
from jinja2 import Template
from assistant.llm import num_tokens_from_string
import json

MAX_TOKENS = 5000


def sql_query(queries, gpt):
    queries_json_str = json.dumps(queries, ensure_ascii=False)
    user_query = SQL_USER_QUERY.render(
        queries_result=queries_json_str, question=gpt.question
    )
    messages = [dict(role="system", content=SQL_SYS_MSG)] + [
        dict(role="user", content=user_query)
    ]
    analysis = gpt.completion(messages=messages, name="SQL", kind="llm")
    return analysis


def review_text(df_reviews, gpt):
    df_s = get_representative_sample(df_reviews, max_tokens=MAX_TOKENS)
    reviews = []
    for group, df_g in df_s.groupby(["company", "category", "similarity_query"]):
        reviews.append(
            dict(
                company=group[0],
                category=group[1],
                similarity_query=group[2],
                reviews=df_g["content"].to_list(),
            )
        )
    reviews_json_str = json.dumps(reviews, ensure_ascii=False)
    user_msg = REVIEW_ANALYSIS_USER_QUERY.render(
        reviews=reviews_json_str, question=gpt.question
    )
    messages = [dict(role="system", content=REVIEW_ANALYSIS_SYS_MSG)] + [
        dict(role="user", content=user_msg)
    ]
    analysis = gpt.completion(messages=messages, name="Review", kind="llm")
    return analysis


def plots(plots, companies, gpt):
    company_descr = (
        f"comany: {companies[0]}" if len(companies) == 1 else f"companies: {companies}"
    )
    sys_msg = PLOT_ANALYSIS_SYS_MSG.render(company=company_descr, question=gpt.question)
    messages = [dict(role="system", content=sys_msg)]
    analysis_msgs = []
    for plot in plots:
        fig, data, plot_descr = plot["fig"], plot["data"], plot["descr"]

        if type(data) == dict:
            user_msg = f"Data visualisation description: {plot_descr}\n\n"
            for company, df in data.items():
                user_msg += f"Company: {company}\n{df.to_csv(index=False)}\n\n"
        else:
            user_msg = PLOT_ANALYSIS_USER_MSG.render(
                plot_descr=plot_descr, data=data.to_csv(index=False)
            )
        messages.append(dict(role="user", content=user_msg))

        gpt.st.plotly_chart(fig, use_container_width=True)
        analysis = gpt.completion(
            messages=messages, model="gpt-4", name="Plot", kind="llm"
        )

        messages.append(dict(role="assistant", content=analysis))

        analysis_msgs.append(dict(role="plot", content=fig))
        analysis_msgs.append(dict(role="assistant", content=analysis))

    return analysis_msgs


def get_representative_sample(df, max_tokens):
    # FIXME: Add take top n reviews sorted by similarity distance if similarity_query is not None
    avg_tokens_pr_review = (
        df["content"]
        .sample(300 if len(df) > 300 else len(df))
        .apply(lambda x: num_tokens_from_string(x, model="gpt-4"))
        .mean()
    )
    n_reviews = int(max_tokens / avg_tokens_pr_review)
    if n_reviews > len(df):
        return df
    else:
        df["combined"] = list(
            zip(df["category"], df["company"], df["similarity_query"])
        )
        weight = df["combined"].value_counts(normalize=True)
        df["combined_weight"] = df["combined"].apply(lambda x: weight[x])
        df_sample = df.sample(n_reviews, weights=df["combined_weight"])
        return df_sample


###   Prompts   ###
SQL_SYS_MSG = """As a skilled analyst specializing in customer reviews, your task is to answer questions about customer reviews using a provided SQL query and corresponding SQL result. The format of a user question is therefore as follows:

Queries:
[
    {
        SQLQuery: "SQL query string",
        SQLResult: "SQL query result"
    },
    /* more queries */
]
Question: "User question that should be answered by the SQL query and SQL result" 

Always answer in the same language as the question."""

SQL_USER_QUERY = Template(
    """Queries:
{{ queries_result }}
Question: {{ question }}"""
)

REVIEW_ANALYSIS_SYS_MSG = """As a skilled analyst specializing in customer review data, your task is to answer questions by analysing the provided reviews. The format of a user question is therefore as follows:

Reviews:
[
    {
        company: "The name of the company the reviews are about",
        category: "The category of the reviews",
        similarity_query: "The similarity query used to find reviews with similar semantic meaning",
        reviews: ["review string", "review string", ...],
        /* Each review string is the content of a unique review */
    },
    /* more reviews of similar or different company and/or category */

]
Question: User question

When responding, ensure to address the specific question asked, and focus on the patterns, trends, and insights derived from reviews. The response should be flexible and adaptable to various relevant and creative questions, emphasizing accuracy and relevance.
Always answer in the same language as the question."""

REVIEW_ANALYSIS_USER_QUERY = Template(
    """Reviews:
{{ reviews }}

Question: {{ question }}"""
)

PLOT_ANALYSIS_SYS_MSG = Template(
    """You are a brilliant data analyst that analyses data related to customer review. You only extract the highlevel patterns and draw conclusions from these highlevel patterns.

Don't be verbose in your answers, but do provide details and examples where it might help the explanation.

You are analysing a data visualisation shown to the user just above your answer. Since you cannot see the data visualisation you are instead provided with a short description of the data visualisation and the raw data in csv format. The reviews are about the {{ company }}.

Analyse the data directly. Do not write code to analyse the data.

When analysing the data try to answer the following questions: {{ question }}

Always answer in the language of the Question.

Start by saying something like "As seen from the above figure" in the language of the Question."""
)


PLOT_ANALYSIS_USER_MSG = Template(
    """Data visualisation description: {{ plot_descr }}

Data used in the visualisation:
{{ data }}"""
)
