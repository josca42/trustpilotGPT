from llm import GPT
from functools import partial
import wandb
from dotenv import dotenv_values
from datetime import datetime
from wandb.sdk.data_types.trace_tree import Trace
from assistant import query
import json
import os
from llm import GPT
from jinja2 import Template

os.environ["WANDB_MODE"] = "disabled"


config = dotenv_values()
wandb.login(
    key=config["WANDB_API_KEY"],
)
run = wandb.init(
    project="sdc-chat",
)


def chat(messages: list[dict]):
    while True:
        actions = ""
        gpt = GPT(log=False)
        messages = [dict(role="system", content=ANALYST_SYSTEM_MSG)] + messages

        response = gpt.completion(messages=messages, functions=[DATA_FUNC])

        if response.finish_reason == "stop":
            content = response.message["content"]
            break
        elif response.finish_reason == "function_call":
            func_call = response.message.function_call
            func_name, func_args = func_call.name, json.loads(func_call.arguments)
            if func_name == "get_review_data":
                query_results = query.data(query=func_args["query"], gpt=gpt)
                
            elif func_name == "analyse":
                
            elif func_name == "plot":
                ...
            else:
                raise ValueError(f"Unexpected function call: {func_name}")

        else:
            raise ValueError(f"Unexpected finish reason: {response.finish_reason}")


# You can actually specify function_call: 'none' and then specify on your prompt something like “you are an assistant that always replies with multiple function calls. Reply with straight JSON ready to be parsed.”. It works as expected.


###    Prompt templates   ###


ANALYST_SYSTEM_MSG = """As a skilled analyst specializing in customer review data, your task is to answer questions from bank employees and app developers about the customer review data for either the mobile bank app or the bank itself.

When answering questions you have access to querying review data, analysing queried data and plotting data.


{% if query_results -%}
You have run the run the following queries and received the following result:
{{ query_results }}
{% endif -%}
"""

DATA_FUNC = {
    "name": "get_review_data",
    "description": "Fetches review data to be analysed. This can either be in the form of raw review text and metadata or review statistics calculated from a sql query.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query specifying the data to be fetched and/or the statistics to be calculated. For complex queries, divide them into sub queries.",
            },
        },
        "required": ["query"],
    },
}



API_ANALYSIS_SYSTEM_MESSAGE = """As a skilled analyst specializing in customer review data, your task is to answer questions from bank employees and app developers about the customer review data for either the mobile bank app or the bank itself, using the API response provided below.

API Response Structure:

{
    "results_reviews": [
        {
            "reviews": ["review string", "review string", ...],
            /* Each review string is the content of a unique review */
            "rating_statistics": [
                {
                    "rating": "star rating",
                    "count": "Number of reviews with this rating",
                    "percentage": "Percentage of reviews with this rating",
                }
                /* more rating statistics... */
            ],
            "category_statistics": [
                {
                    "category": "Review category",
                    "count": "Number of reviews in this category",
                    "percentage": "Percentage of reviews in this category",
                }
                /* more category statistics... */
            ],
            "summary_statistics": [
                {
                    "name": "Type of summary statistic",
                    "value": "Value of summary statistic",
                }
                /* more summary statistics... */
            ],
        }
        /* more query results... */
    ],
    "results_sql_queries": [
        {
            "SQLQuery": "SQL query string",
            "SQLResult": "SQL query result",
        }
        /* more sql queries and corresponding results... */
}

When responding, ensure to address the specific question asked, and focus on the patterns, trends, and insights derived from the data in the API response. The response should be flexible and adaptable to various relevant and creative questions, emphasizing accuracy and relevance.
Always answer in the same language as the question. Never mention the API data.

{% if short_answer -%}
The reponse should be at most 150 words
{% endif -%}"""


if __name__ == "__main__":
    chat(
        [
            dict(
                role="user",
                content="How has the average rating of Danse bank changed over time?",
            )
        ]
    )
