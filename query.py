import pandas as pd
from copy import deepcopy
import openai
import json
import jinja2
from json.decoder import JSONDecodeError
from datetime import datetime
import json5
from datetime import datetime
from utils import gpt_stream_completion
from funcs.data import get_data


def data(query: str, st_msg_placeholder):
    json_request_string = query_to_request_json(query, st_msg_placeholder)
    json_request = parse_request_string(json_request_string)
    review_queries, stats_queries = extract_queries(json_request)

    data = get_data(json_request)
    # FIXME do some processing on the data
    return data


def query_to_request_json(query: str, st_msg_placeholder) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_msg = dict(
        role="system",
        content=API_CALL_SYSTEM_MSG_TEMPLATE.render(current_date=current_date),
    )
    chat_msgs = API_CALL_EXAMPLES + [dict(role="user", content=query)]
    json_request_string = gpt_stream_completion(
        messages=[system_msg, *chat_msgs], st_msg_placeholder=st_msg_placeholder
    )
    return json_request_string


def parse_request_string(json_request_string: str):
    try:
        json_request = json.loads(json_request_string)
    except JSONDecodeError:
        try:
            json_request = json5.loads(json_request_string)
        except:
            raise Exception(
                f"Could not decode JSON request string: {json_request_string}"
            )
    return json_request


def extract_queries(json_request):
    review_queries, stats_queries = [], []
    for q in json_request:
        retrieve = q.pop("retrieve", None)
        if retrieve == "statistics":
            stats_queries.append(q)
        else:
            review_queries.append(q)
    return review_queries, stats_queries


###    Prompt templates    ###
jinja_env = jinja2.Environment()

API_CALL_SYSTEM_MESSAGE = """Your task is to convert a given question into an API request using the JSON format shown below, which contains an array of queries. Keep in mind the guidelines for each field in the query object while converting the question.

```json
{
  "queries": [
    {
      "source": "app or bank",
      "date_range": {
        "start": "start date",
        "end": "end date"
      },
      "category": "category type",
      "bank": "bank name",
      "country": "country code",
      "similarity_query": "similarity query text"
      "retrieve": "reviews or statistics",
    }
  ]
}
```

Guidelines for query object fields:

1. source: Mandatory field. Set as 'app' for mobile bank app reviews and 'bank' for general bank reviews.
2. date_range: Include 'start' and 'end' fields in 'yyyy-mm-dd' format when specified in the question, otherwise, omit this field. The current date is {{ current_date }}.
3. category: Set this field to one of the given values when a review type is mentioned, otherwise, omit it: 'other', 'functionality', 'ui', 'error', 'stability', 'customer service', 'counseling', 'mobile/web bank', 'fees and interest rates'.
4. bank: Mention the bank's name if the question is about a specific bank, otherwise, omit this field.
5. country: Use the respective country code (e.g., 'DK', 'NO', 'SE', 'FO', 'UK', 'NZ') if a specific country is mentioned, otherwise, omit this field.
6. similarity_query: Set this field with the query text if a specific semantic query is mentioned, otherwise, omit it.
7. retrieve: Set as 'reviews' to retrieve reviews and 'statistics' to retrieve statistics. If not specified, the default value is 'reviews'.

For complex questions, divide them into sub-questions and refine results using the parameters 'date_range', 'category', 'bank', and 'country', with the optional 'similarity_query' for querying or ordering by semantic similarity. Ensure you accurately transform the question into the JSON structure, taking care to attend to the subtleties and details provided in the prompt."""

API_CALL_SYSTEM_MSG_TEMPLATE = jinja_env.from_string(API_CALL_SYSTEM_MESSAGE)

API_CALL_EXAMPLES = [
    dict(
        role="user",
        content="Hvilke funktioner i DnB appen som kunderne er mest glade for findes ikke i SDC appen?",
    ),
    dict(
        role="assistant",
        content="""{
    "queries": [
        {
            "source": "app",
            "bank": "DnB",
            "category": "functionality",
            "similarity_query": "positive review"
        },
        {
            "source": "app",
            "bank": "SDC",
            "category": "functionality",
            "similarity_query": "feature request"
        }
    ]
}""",
    ),
    dict(
        role="user",
        content="Kan kunder bedst lide SDC appen eller BEC appen eller Bankdata appen eller danske bank appen målt på anmeldelser givet efter d. 31. januar 2023",
    ),
    dict(
        role="assistant",
        content="""{
    "queries": [
        {"source": "app", "bank": "SDC", "date_range": {"start": "2023-02-01"}},
        {"source": "app", "bank": "BEC", "date_range": {"start": "2023-02-01"}},
        {"source": "app", "bank": "Bankdata", "date_range": {"start": "2023-02-01"}},
        {"source": "app", "bank": "Danske Bank", "date_range": {"start": "2023-02-01"}}
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
            {"source": "bank", "country": "NO", "category": "customer service", "retrieve": "statistics"}
        ]
    }""",
    ),
]
