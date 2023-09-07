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
from copy import copy


def chat(messages: list[dict], st: streamlit = None):
    gpt = GPT(log=True, question=messages[-1]["content"], st=st)

    with gpt.st.status("Working"):
        metadata = extract_metadata(messages, gpt)
        plan = create_plan(messages, gpt)

    analysis_msgs = []
    for step in plan:
        action, action_array = step.split(":")
        action = action.strip()
        action_array = ast.literal_eval(action_array.strip())

        if action == "SQL":
            queries_result = query.sql(queries=action_array, metadata=metadata, gpt=gpt)
            analysis = analyse.sql_query(queries=queries_result, gpt=gpt)
        elif action == "PLOT":
            plots = plot.create(metadata=metadata, plots=action_array)
            analysis = analyse.plots(
                plots=plots, companies=metadata["companies"], gpt=gpt
            )
        elif action == "ANALYSE REVIEWS":
            df_reviews = query.data(queries=action_array, metadata=metadata)
            analysis = analyse.review_text(df_reviews=df_reviews, gpt=gpt)
        else:
            raise ValueError(f"Unexpected action: {action}")

        if type(analysis) == str:
            analysis_msgs.append(dict(role="assistant", content=analysis))
        else:
            analysis_msgs.extend(analysis)

    output = [dict(role="assistant", content=m) for m in [metadata, plan]] + [
        m for m in analysis_msgs if m["role"] != "plot"
    ]
    gpt.root_span.outputs = {"assistant": output}
    gpt.finish()
    return analysis_msgs


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
        name="Metadata",
        kind="chain",
    )
    metadata = json.loads(response_txt)
    metadata["companies"] = [
        crud.company.most_similar_name(company) for company in metadata["companies"]
    ]
    metadata["start_date"] = str2date(metadata["start_date"])
    metadata["end_date"] = str2date(metadata["end_date"])
    return metadata


def create_plan(messages: list[dict], gpt):
    response_txt = gpt.completion(
        messages=[dict(role="system", content=PLANNER_SYS_MSG)]
        + PLANNER_EXAMPLES
        + messages,
        name="Plan",
        kind="chain",
    )
    plan = extract_array(response_txt)
    return plan


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
SQL: Sends array of relevant questions to a sql agent that returns answers to the question by creating a SQL query for each question and interpreting SQL result.
PLOT: Sends array of relevant plots to a plot agent that returns the plots. The following plots are available: 'ratings piechart for single company', 'ratings piecharts by review category for single company', 'ratings time series for single company', 'ratings and review count time series comparing companies', 'ratings distribution comparing companies'. The action does not need a GET action to fetch data.
ANALYSE REVIEWS: Sends an array of natural language queries to a database of reviews. The database finds the reviews most semantically similar to the queries. The text of the reviews are then analysed and summarised.

When writing the list of steps to take do not include company names or dates.

Return the response as a formatted array of strings that can be used in JSON.parse()"""

PLANNER_EXAMPLES = [
    dict(
        role="user",
        content="Hvilket firma har den højeste gennemsnitlige rating siden 1 januar 2023",
    ),
    dict(
        role="assistant",
        content="""["SQL: ['Which company has the highest average rating?']"]""",
    ),
    dict(
        role="user",
        content="Hvordan har folk anmeldt Danske Bank siden 1 januar 2023?",
    ),
    dict(
        role="assistant",
        content="""[
"PLOT: ['ratings time series for single company', 'ratings piechart for single company']", "ANALYSE REVIEWS: ['Negative feedback', 'Positive feedback']"
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
 ]""",
    ),
]


METADATA_EXTRACTION_SYS_MSG = Template(
    """You are a metadata extraction agent. You extract relevant metadata from questions. You specifically extract relevant company names, start date and end date and categories. Only extract categories if a category like one of the following categories are mentioned: 'customer service', 'counseling', 'mobile/web bank', 'fees and interest rates'. If a date is extracted write the date in 'yyyy-mm-dd'. The current date is {{ current_date }}.
 
You return the results on the following form:

{
"companies": [],
"start_date": "",
"end_date": "",
"categories": []
}

If the question does not mention any company names then let the companies list be empty. Likewise if no categories are mentioned you let the category list be empty. If no start date and/or end date is mentioned then let the date be an empty string."""
)


if __name__ == "__main__":
    chat(
        [
            dict(
                role="user",
                content="Hvilket firma har flest anmeldelser?",
            )
        ],
        st=None,
    )


ex_1 = "Hvilkt firma foretrækker folk af hhv. Danske Bank, Lunar og Frøs Sparekasse?"
ex_2 = "Hvordan har danske banks rating udviklet sig siden 1 januar 2023"
