import wandb
from dotenv import dotenv_values
from wandb.sdk.data_types.trace_tree import Trace
from assistant import query
import json
import ast
import re
from assistant.llm import GPT
from jinja2 import Template
from assistant.config import config
from assistant.db import crud
from assistant import query, plot, analyse
import os
import pandas as pd
from datetime import datetime
import streamlit

os.environ["WANDB_MODE"] = "disabled"


wandb.login(
    key=config["WANDB_API_KEY"],
)
run = wandb.init(
    project="sdc-chat",
)


def chat(messages: list[dict], st: streamlit = None):
    gpt = GPT(log=False, st=st)
    # metadata = extract_metadata(messages, gpt)
    # plan = create_plan(messages, gpt)

    metadata = {
        "companies": ["Danske Bank", "Lunar", "Frøs Sparekasse"],
        "start_date": "",
        "end_date": "",
        "categories": [],
    }
    plan = [
        "PLOT: ['ratings and review count time series comparing companies', 'ratings distribution comparing companies']",
        "GET: Fetch data",
        "ANALYSE REVIEWS: Summarise the reviews",
    ]
    question = messages[-1]["content"]
    for step in plan:
        action, action_input = [a.strip() for a in step.split(":")]
        if action == "SQL":
            query_sql = query.sql(query=action_input, metadata=metadata, gpt=gpt)
            sql_analysis = analyse.sql_query(
                query=query_sql, question=question, gpt=gpt
            )
        elif action == "GET":
            query_data = query.data(plan=plan, metadata=metadata)
        elif action == "PLOT":
            fig = plot.create(metadata=metadata, plots=action_input, gpt=gpt)
            break
        elif action == "ANALYSE REVIEWS":
            review_text_analysis = analyse.review_text(
                query_data=query_data, question=question, gpt=gpt
            )
            pass
        else:
            raise ValueError(f"Unexpected action: {action}")

    return st, messages


def create_plan(messages: list[dict], gpt):
    response_txt = gpt.completion(
        messages=[dict(role="system", content=PLANNER_SYS_MSG)]
        + PLANNER_EXAMPLES
        + messages,
        model="gpt-4",
        use_expander=True,
        name="Create plan",
    )
    plan = extract_array(response_txt)
    return plan


def extract_metadata(messages: list[dict], gpt):
    response_txt = gpt.completion(
        messages=[
            dict(
                role="system",
                content=METADATA_EXTRACTION_SYS_MSG.render(
                    current_date=datetime.now().strftime("%Y-%m-%d")
                ),
            )
        ]
        + messages,
        model="gpt-3.5-turbo",
        use_expander=True,
        name="Extract metadata",
    )
    metadata = json.loads(response_txt)
    metadata["companies"] = [
        crud.company.most_similar_name(company) for company in metadata["companies"]
    ]
    metadata["start_date"] = str2date(metadata["start_date"])
    metadata["end_date"] = str2date(metadata["end_date"])
    return metadata


def extract_array(input_str: str) -> list[str]:
    regex = (
        r"\[\s*\]|"  # Empty array check
        r"(\[(?:\s*(?:\"(?:[^\"\\]|\\.)*\"|\'(?:[^\'\\]|\\.)*\')\s*,?)*\s*\])"
    )
    match = re.search(regex, input_str)
    if match is not None:
        return ast.literal_eval(match[0])
    else:
        return []


def str2date(date_str):
    if date_str == "":
        return ""
    else:
        try:
            return pd.to_datetime(date_str).date()
        except:
            return ""


###   Prompts  ###
PLANNER_SYS_MSG = """You are a task creation AI called AgentGPT. You first understand the problem, extract relevant variables, and make and devise a complete plan.

You are answering questions from users about customer reviews of companies on Trustpilot. Create a list of step by step actions to accomplish the goal. Use at most 4 steps.

You can take the following actions:
SQL: Sends the question to a sql agent that creates a SQL query that answers the question. Returns the result of the SQL query.
GET: Sends the question to a data agent that gets relevant data. Returns the data.
PLOT: Sends array of relevant plots to a plot agent that returns the plots. The following plots are available: 'ratings piechart for single company', 'ratings piecharts by review category for single company', 'ratings time series for single company', 'ratings and review count time series comparing companies', 'ratings distribution comparing companies'. The action does not need a GET action to fetch data.
ANALYSE REVIEWS: Summarise, interpret and extract patterns from the text content of the reviews fetched by the GET action.

Return the response as a formatted array of strings that can be used in JSON.parse()"""

PLANNER_EXAMPLES = [
    dict(
        role="user",
        content="Hvilket firma har den højeste gennemsnitlige rating",
    ),
    dict(
        role="assistant",
        content="""["SQL: Which company has the highest average rating?"]""",
    ),
    dict(
        role="user",
        content="Hvordan har folk anmeldt Danske Bank?",
    ),
    dict(
        role="assistant",
        content="""[
"PLOT: ['ratings time series for single company', 'ratings piecharts by review category for single company']",
"GET: Fetch data",
"ANALYSE REVIEWS: Summarise the reviews",
 ]""",
    ),
    dict(
        role="user",
        content="Hvilket firma kan folk bedste lide af hhv. Danske Bank, Lunar eller Nordea målt på anmeldelser efter 1 januar 2023?",
    ),
    dict(
        role="assistant",
        content="""[
"PLOT: ['ratings and review count time series comparing companies', 'ratings distribution comparing companies']",
"GET: Fetch data",
"ANALYSE REVIEWS: Summarise the reviews",
 ]""",
    ),
]


"GET: Fetch the average ratings for Danske Bank, Lunar, and Nordea after 1st January 2023", "PLOT: 'ratings distribution comparing companies'", "ANALYSE REVIEWS: Summarise and interpret the reviews for Danske Bank, Lunar, and Nordea after 1st January 2023"

METADATA_EXTRACTION_SYS_MSG = Template(
    """You are a metadata extraction agent. You extract relevant metadata from questions. You specifically extract relevant company names, start date and end date and categories. Only extract categories if a category like one of the following categories are mentioned: 'customer service', 'counseling', 'mobile/web bank', 'fees and interest rates'. If a date is extracted write the date in 'yyyy-mm-dd'. The current date is {{ current_date }}.
 
You return the results on the following form:

{
companies: [],
start_date: "",
end_date: "",
categories: []
}

If the question does not mention any company names then let the companies list be empty. Likewise if no categories are mentioned you let the category list be empty. If no start date and/or end date is mentioned then let the date be an empty string."""
)


if __name__ == "__main__":
    chat(
        [
            dict(
                role="user",
                content="Hvilkt firma foretrækker folk af hhv. Danske Bank, Lunar og Frøs Sparekasse?",
            )
        ],
        st=None,
    )
