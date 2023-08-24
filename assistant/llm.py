import tiktoken
import openai
from typing import Union, Optional
from dotenv import dotenv_values
import cohere
import wandb
from wandb.sdk.data_types.trace_tree import Trace
import os
from datetime import datetime

os.environ["WANDB_MODE"] = "disabled"

config = dotenv_values()
wandb.login(
    key=config["WANDB_API_KEY"],
)
run = wandb.init(
    project="sdc-chat",
)

config = dotenv_values()

LLM_cohere = cohere.Client(config["COHERE_API_KEY"])


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def embed(texts: Union[list[str], str]):
    if isinstance(texts, str):
        texts = [texts]
    texts = [text.replace("\n", " ") for text in texts]

    response = openai.Embedding.create(
        input=texts,
        model="text-embedding-ada-002",
    )
    return [data.get("embedding") for data in response.data]


class GPT:
    def __init__(self, log) -> None:
        self.user_conversation = []
        self.steps = []
        self.log = log
        self.root_span = None
        self.st_msg_placeholder = None

        if log:
            self.root_span = Trace(
                name="Chat",
                kind="agent",
                start_time_ms=timestamp(),
                metadata={"user": "josca"},
            )

    def completion(
        self,
        messages,
        model="gpt-3.5-turbo-0613",
        temperature=0,
        functions=[],
        stop=None,
        name="",
        stream=False,
    ):
        start = timestamp()

        if functions:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                functions=functions,
                stream=stream,
            )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stop=stop,
                stream=stream,
            )

        if stream and self.st_msg_placeholder is not None:
            full_response = ""
            for chunk in response:
                full_response += chunk.choices[0].delta.get("content", "")
                self.st_msg_placeholder.markdown(full_response + "▌")

        if self.log:
            self.root_span.add_child(
                Trace(
                    name=name,
                    start_time_ms=start,
                    end_time_ms=timestamp(),
                    inputs=wandb_format_msgs(messages),
                    outputs=wandb_format_response(response),
                )
            )

        return response.choices[0]

    def finish(self):
        self.root_span.end_time_ms = timestamp()
        self.root_span.log("chat_test")


def timestamp():
    return round(datetime.now().timestamp() * 1000)


def wandb_format_msgs(msgs):
    return {msg["role"]: msg["content"] for msg in msgs}


def wandb_format_response(response):
    response = response.choices[0]
    if response.finish_reason == "function_call":
        func_call = response.message.function_call
        return {func_call.name: func_call.arguments}
    else:
        return response.message["content"]
