from llm import gpt_completion
from functools import partial
import wandb
from dotenv import dotenv_values
from datetime import datetime
from wandb.sdk.data_types.trace_tree import Trace
import query
import json
import os

os.environ["WANDB_MODE"] = "disabled"


config = dotenv_values()
wandb.login(
    key=config["WANDB_API_KEY"],
)
run = wandb.init(
    project="sdc-chat",
)


def chat(messages: list[dict]):
    start = timestamp()
    root_span = Trace(
        name="Chat", kind="agent", start_time_ms=start, metadata={"user": "josca"}
    )

    response = gpt_analyst(messages=messages)
    trace = Trace(
        name="analyst",
        kind="llm",
        start_time_ms=start,
        end_time_ms=timestamp(),
        parent=root_span,
        inputs=wandb_format_msgs(messages),
        outputs=wandb_format_response(response),
    )
    root_span.add_child(trace)

    if response.finish_reason == "function_call":
        func_call = response.message.function_call
        func_name, func_args = func_call.name, json.loads(func_call.arguments)
        if func_name == "get_review_data":
            query.data(query=func_args["query"])

    else:
        content = response.message["content"]

    root_span.end_time_ms = timestamp()
    root_span.log("chat_test")


def timestamp():
    return round(datetime.now().timestamp() * 1000)


def wandb_format_msgs(msgs):
    return {msg["role"]: msg["content"] for msg in msgs}


def wandb_format_response(response):
    if response.finish_reason == "function_call":
        func_call = response.message.function_call
        return {func_call.name: func_call.arguments}
    else:
        return response.message["content"]


# You can actually specify function_call: 'none' and then specify on your prompt something like “you are an assistant that always replies with multiple function calls. Reply with straight JSON ready to be parsed.”. It works as expected.


###    Prompt templates   ###


ANALYST_SYSTEM_MSG = """As a skilled analyst specializing in customer review data, your task is to answer questions from bank employees and app developers about the customer review data for either the mobile bank app or the bank itself.

When answering questions you have access to querying review data, analysing queried data and plotting data."""

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

gpt_analyst = partial(
    gpt_completion, system_msg=ANALYST_SYSTEM_MSG, temperature=0, functions=[DATA_FUNC]
)


if __name__ == "__main__":
    chat([dict(role="user", content="What is the average rating of the app?")])
