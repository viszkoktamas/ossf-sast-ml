import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "gemini-3-pro-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "file_name": {"type": "STRING"},
            "start_line": {"type": "INTEGER"},
            "end_line": {"type": "INTEGER"},
            "is_vulnerable": {"type": "BOOLEAN"},
        },
        "required": ["file_name", "start_line", "end_line", "is_vulnerable"]
    }
}

SYSTEM_PROMPT = "You are an expert SAST tool. Evaluate each function in the list and return the JSON array."


def _get_headers():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set the GEMINI_API_KEY environment variable.")

    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }


def _get_payload(functions_list, thinking_level):
    prompt_text = "Analyze the following functions and return the JSON array. Ensure you echo the file_name, start_line, and end_line for each result.\n\n"
    for func in functions_list:
        prompt_text += f"--- File: {func['file_name']} | Lines: {func['start_line']}-{func['end_line']} ---\n{func['body']}\n\n"

    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "thinkingConfig": {"thinkingLevel": thinking_level},
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA
        }
    }


def call_gemini(functions_list, thinking_level="HIGH", max_retries=5):
    base_wait_time = 5
    for attempt in range(max_retries):
        response = requests.post(URL, headers=_get_headers(), json=_get_payload(functions_list, thinking_level))

        if response.status_code == 200:
            try:
                return json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])

            except Exception as e:
                raise ValueError(f"Parsing error: {str(e)}, raw: {result}")

        elif response.status_code == 429:
            if attempt < max_retries - 1:
                wait_time = base_wait_time * (2 ** attempt)
                time.sleep(wait_time)

        elif response.status_code in [500, 503]:
            if attempt < max_retries - 1:
                time.sleep(10)

            else:
                raise ValueError(f"API Error {response.status_code}: {response.text}")

        else:
            raise ValueError(f"API Error {response.status_code}: {response.text}")

    raise ValueError("Failed: Max retries reached.")


def predict(functions_list):
    return call_gemini(functions_list)


if __name__ == "__main__":
    with open("test.json", 'r', encoding='utf-8') as f:
        test_function_body = json.load(f)[0]["messages"][0]["functionBody"]

    result = predict(test_function_body)
    print(result)
