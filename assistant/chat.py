import wandb
from dotenv import dotenv_values
from datetime import datetime
from wandb.sdk.data_types.trace_tree import Trace
from assistant import query
from assistant.funcs.plot import create_plot
import json
import ast
import re
from assistant.llm import GPT
from jinja2 import Template
from assistant.config import config
import os

os.environ["WANDB_MODE"] = "disabled"


wandb.login(
    key=config["WANDB_API_KEY"],
)
run = wandb.init(
    project="sdc-chat",
)


def chat(messages: list[dict], st):
    gpt = GPT(log=False)
    # Make plan for the task
    plan = create_plan(messages, gpt)

    for step in plan:
        action, action_input = step.split(":")
        if action == "SQL":

        elif action == "GET":
        
        elif action == "PLOT":
        
        elif action == "ANALYSE DATA":
        
        elif action == "ANALYSE REVIEWS":
        
        else:
            raise ValueError(f"Unexpected action: {action}")

        elif response.finish_reason == "function_call":
            func_call = response.message.function_call
            func_name, func_kwargs = func_call.name, json.loads(func_call.arguments)
            if func_name == "get_review_data":
                results = query.data(query=func_kwargs["query"], gpt=gpt)
                results_data, results_str = [], []
                for result in results:
                    if "data" in result:
                        data = result.pop("data")
                        results_str.append(result.copy())
                        result["SQLResult"] = data
                        results_data.append(result)
                    else:
                        results_str.append(result)
                        results_data.append(result)

                results_str = json.dumps(results_str, ensure_ascii=False)
                messages.append(
                    dict(
                        role="function",
                        name="get_review_data",
                        content=f"Query results:\n\n{results_str}",
                    )
                )

            elif func_name == "analyse":
                analyze(results_data, gpt)
            elif func_name == "plot":
                fig = create_plot(**func_kwargs)
                st.plotly_chart(fig)

                messages.append(
                    dict(
                        role="function",
                        name="plot",
                        content=f"The function has just plotted a {func_kwargs['plot_type']} figure for companies {func_kwargs['companies']}",
                    )
                )
            else:
                raise ValueError(f"Unexpected function call: {func_name}")

        else:
            raise ValueError(f"Unexpected finish reason: {response.finish_reason}")

    return messages, st


def create_plan(messages: list[dict], gpt):
    response = gpt.completion(
        messages=[dict(role="system", content=PLANNER_SYSTEM_MSG)] + messages
    )
    plan = extract_array(response.message.content)
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
        return handle_multiline_string(input_str)


def handle_multiline_string(input_str: str) -> list[str]:
    # Handle multiline string as a list
    processed_lines = [
        re.sub(r".*?(\d+\..+)", r"\1", line).strip()
        for line in input_str.split("\n")
        if line.strip() != ""
    ]

    # Check if there is at least one line that starts with a digit and a period
    if any(re.match(r"\d+\..+", line) for line in processed_lines):
        return processed_lines
    else:
        raise RuntimeError(f"Failed to extract array from {input_str}")


# You can actually specify function_call: 'none' and then specify on your prompt something like “you are an assistant that always replies with multiple function calls. Reply with straight JSON ready to be parsed.”. It works as expected.


###    Prompt templates   ###


PLANNER_SYSTEM_MSG = """You are a task creation AI called AgentGPT. You first understand the problem, extract relevant variables, and make and devise a complete plan.

You are answering questions from users about customer reviews of companies on Trustpilot. Create a list of step by step actions to accomplish the goal. Use at most 4 steps.

You can take the following actions:
SQL: Sends the question to a sql agent that creates a SQL query that answers the question. Returns the result of the SQL query.
GET: Sends the question to a data agent that gets relevant data. Returns the data.
PLOT: Creates a plot. The following plots are available: 'ratings piechart', 'ratings piecharts by category', 'ratings time series'. The action does not need a GET action to fetch data.
ANALYSE DATA: Create data analysis of the data fetched by the GET action.
ANALYSE REVIEWS: Summarise, interpret or extract patterns from the review text.

If the question can be answered by a SQL query then only take one action, SQL.

Return the response as a formatted array of strings that can be used in JSON.parse()"""


# API_ANALYSIS_SYSTEM_MESSAGE = """As a skilled analyst specializing in customer review data, your task is to answer questions from bank employees and app developers about the customer review data for either the mobile bank app or the bank itself, using the API response provided below.

# API Response Structure:

# [

#     {
#         review_query: "The review query string",
#         reviews: ["review string", "review string", ...],
#         /* Each review string is the content of a unique review */
#     },
#     {
#             "SQLQuery": "SQL query string",
#             "SQLResult": "SQL query result",
#             "SQLResultDescription": "Description of the SQL query result",
#     }
# ]

# When responding, ensure to address the specific question asked, and focus on the patterns, trends, and insights derived from the data in the API response. The response should be flexible and adaptable to various relevant and creative questions, emphasizing accuracy and relevance.
# Always answer in the same language as the question. Never mention the API data.

# {% if short_answer -%}
# The reponse should be at most 150 words
# {% endif -%}"""


if __name__ == "__main__":
    chat(
        [
            dict(
                role="user",
                content="Hvilken bank kan folk bedste lide af hhv. Danske Bank, Lunar og Nordea",
            )
        ],
        st=None,
    )
