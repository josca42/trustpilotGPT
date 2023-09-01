import pandas as pd
from copy import deepcopy
import openai
import json
from jinja2 import Template
from json.decoder import JSONDecodeError
from datetime import datetime
from datetime import datetime
from assistant.funcs.data import query_data


def data(query: str, gpt):
    json_request_string = query_to_request_json(query, gpt)
    queries = parse_request_string(json_request_string)
    results = query_data(queries, gpt)
    # FIXME do some processing on the data
    return results


def query_to_request_json(query: str, gpt) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_msg = API_CALL_SYSTEM_MESSAGE.render(current_date=current_date)
    messages = (
        [dict(role="system", content=system_msg)]
        + API_CALL_EXAMPLES
        + [dict(role="user", content=query)]
    )
    json_request_string = gpt.completion(messages=messages, model="gpt-3.5-turbo")
    return json_request_string.message.content


def parse_request_string(json_request_string: str):
    try:
        json_request = json.loads(json_request_string)
    except JSONDecodeError:
        raise Exception(f"Could not decode JSON request string: {json_request_string}")
    return json_request["queries"]


###    Prompt templates    ###

API_CALL_SYSTEM_MESSAGE = Template(
    """Your task is to convert a given question into an API request using the JSON format shown below, which contains an array of queries. Keep in mind the guidelines for each field in the query object while converting the question.

```json
{
  "queries": [
    {
      "date_range": {
        "start": "start date",
        "end": "end date"
      },
      "category": "category type",
      "company": "company name",
      "country": "country code",
      "similarity_query": "similarity query text"
    }
  ]
}
```

Guidelines for query object fields:

1. date_range: Include 'start' and 'end' fields in 'yyyy-mm-dd' format when specified in the question, otherwise, omit this field. The current date is {{ current_date }}.
2. category: Set this field to one of the given values when a review type is mentioned, otherwise, omit it: 'customer service', 'counseling', 'mobile/web bank', 'fees and interest rates'.
3. company: Mention the company's name if the question is about a specific company, otherwise, omit this field.
4. country: Use the respective country code (e.g., 'DK', 'NO', 'SE', 'FO') if a specific country is mentioned, otherwise, omit this field.
5. similarity_query: Set this field with the query text if a specific semantic query is mentioned, otherwise, omit it.

For complex questions, divide them into sub-questions and refine results using the parameters 'date_range', 'category', 'company', and 'country', with the optional 'similarity_query' for querying or ordering by semantic similarity. Ensure you accurately transform the question into the JSON structure, taking care to attend to the subtleties and details provided in the prompt."""
)

API_CALL_EXAMPLES = [
    dict(
        role="user",
        content="Hvad siger kunderne om hhv. Danske Bank, Lunar eller Bankdata ud fra anmeldelser givet efter d. 31. januar 2023",
    ),
    dict(
        role="assistant",
        content="""{
    "queries": [
        {"company": "Danske Bank", "date_range": {"start": "2023-02-01"}},
        {"company": "Lunar", "date_range": {"start": "2023-02-01"}},
        {"company": "Bankdata", "date_range": {"start": "2023-02-01"}},
    ]
}""",
    ),
    dict(
        role="user",
        content="Hvilken bank har den højeste gennemsnitlige rating for kundeservice i Norge?",
    ),
    dict(
        role="assistant",
        content="""{
        "queries": [
            {"country": "NO", "category": "customer service", "query": "What company has the highest average rating?"}
        ]
    }""",
    ),
]
