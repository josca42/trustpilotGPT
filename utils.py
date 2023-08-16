import tiktoken
import openai


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def gpt_stream_completion(messages, st_msg_placeholder, temperature=0, functions=[]):
    # if functions:
    #     response = openai.ChatCompletion.create(
    #         model="gpt-4",
    #         messages=messages,
    #         temperature=temperature,
    #         function_call=functions,
    #         stream=True,
    #     )
    # else:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in response:
        full_response += chunk.choices[0].delta.get("content", "")
        st_msg_placeholder.markdown(full_response + "▌")
    return full_response


def gpt_completion(messages, temperature=0, functions=[], stop=None):
    if functions:
        response = openai.Completion.create(
            model="gpt-4",
            prompt=messages,
            temperature=temperature,
            function_call=functions,
        )
    else:
        response = openai.Completion.create(
            model="gpt-4",
            prompt=messages,
            temperature=temperature,
            stop=stop,
        )
    return response.choices[0].message["content"]
