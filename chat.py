def conversation(messages=[]):
    ...


def data():
    ...


def analyse():
    ...

You can actually specify function_call: 'none' and then specify on your prompt something like “you are an assistant that always replies with multiple function calls. Reply with straight JSON ready to be parsed.”. It works as expected.


get_data_func = {
    "name": "get_data",
    "description": "Creates product web pages. The current date is {{ current_date }} ",
    "parameters": {
        "type": "object",
        "properties": {
            "type": "array",
            "items": {
                "source": {
                    "type": "string",
                    "description": "Data source. Set as 'app' for mobile bank app reviews and 'bank' for general bank reviews.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date of the date range. Format: YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date of the date range. Format: YYYY-MM-DD",
                },
                "category": {
                    "type": "category",
                    "description": "Type of review",
                    "enum": [
                        "other",
                        "functionality",
                        "ui",
                        "error",
                        "stability",
                        "customer service",
                        "counseling",
                        "mobile/web bank",
                        "fees and interest rates",
                    ],
                },
                "bank": {"type": "string", "description": "Bank name"},
                "country": {"type": "string", "description": "Country name"},
                "similarity_query": {
                    "type": "string",
                    "description": "Semantic similarity query text. Use to get reviews with similar meaning to the similarity_query.",
                },
                "retrieval_method": {
                    "type": "string",
                    "description": "Set as 'reviews' to retrieve reviews and 'statistics' to retrieve statistics. If not specified, the default value is 'reviews'.",
                },
            },
        },
        "required": ["source"],
    },
}

{
    name: "get_weather",
    description: "Get weather from given locations and datetimes",
    parameters: {
        type: "object",
        properties: {
            locations: {
                type: "array",
                items: {
                    type: "object",
                    properties: {
                        name: {
                            type: "string",
                            description: "Name of location, e.g. San Francisco, CA",
                        },
                        datetime: {
                            type: "string",
                            description: "Date or time, e.g. today, tomorrow, 2023-06-29",
                        },
                    },
                },
            }
        },
        required: ["locations"],
    },
}

