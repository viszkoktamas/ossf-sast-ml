import json

import requests

URL = "http://host.docker.internal:8765/predict"


def _get_payload(functions_list):
    return {
        "functions": [func['body'] for func in functions_list]
    }


def call_llm(functions_list):
    response = requests.post(URL, json=_get_payload(functions_list))
    return response.json()["predictions"]


def predict(functions_list):
    preds = call_llm(functions_list)
    for f, p in zip(functions_list, preds):
        f["is_vulnerable"] = p
        del f["body"]

    return functions_list


if __name__ == "__main__":
    functions_list = []
    with open("test.json", 'r', encoding='utf-8') as f:
        for f in json.load(f):
            for m in f["messages"]:
                functions_list.append({
                    "file_name": f["filePath"],
                    "start_line": m["startLine"],
                    "end_line": m["endLine"],
                    "body": m["functionBody"]
                })

    result = predict(functions_list)
    print(result)
