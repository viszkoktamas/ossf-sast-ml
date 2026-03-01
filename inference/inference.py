import json
import argparse
import hashlib
import pickle
from collections import defaultdict

from pathlib import Path

from prediction import predict


def _get_pickle_prefix(run_id):
    return Path(__file__).parent / 'cache' / run_id


def _get_pickle_key(function_body):
    return hashlib.sha512(function_body.encode('utf-8')).hexdigest()


def _load_pickled_result(pickle_file):
    try:
        if pickle_file.exists():
            with open(pickle_file, 'rb') as f:
                return pickle.load(f)

    except Exception as e:
        print(f"Error loading pickled result {pickle_file}: {e}")

    return None


def _write_pickled_result(pickle_file, prediction):
    pickle_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pickle_file, 'wb') as f:
        pickle.dump(prediction, f)


def _interval_contains(a_start, a_end, b_start, b_end):
    return a_start <= b_start and a_end >= b_end


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input json containing function data")
    parser.add_argument("-r", "--run_id", help="run id")
    return parser.parse_args()


def _get_function_key(file_path, start, end):
    return f"{file_path}({start},{end})"


def main(input_file, run_id=None):
    """
    input format:
[
  {
    "filePath": "C:\\...\\karma.conf.js",
    "messages": [
      {
        "functionBody": "function(config) {...}",
        "startLine": 3,
        "endLine": 36,
        "nodeType": "FunctionExpression"
      }, ...
    ]
  }, ...
]
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        function_data = json.load(f)

    pickle_prefix = _get_pickle_prefix(run_id or 'run_1')
    pickled_results = list()
    calculate_functions = dict()
    result_data = []
    for file_data in function_data:
        file_path = file_data.get("filePath", "")
        alerts = sorted(file_data.get("messages", []), key=lambda m: m.get("startLine", 0))
        for a in alerts:
            start = a.get("startLine", 0)
            end = a.get("endLine", 0)
            function_body = a.get("functionBody")
            if not function_body:
                continue

            function_body_hash = hashlib.sha512(function_body.encode('utf-8')).hexdigest()
            pickle_file = pickle_prefix / function_body_hash
            pickled_result = _load_pickled_result(pickle_file=pickle_file)
            if pickled_result is None:
                calculate_functions[_get_function_key(file_path, start, end)] = {
                    "hash": function_body_hash,
                    "file_name": file_path,
                    "start_line": start,
                    "end_line": end,
                    "body": function_body,
                }

            else:
                pickled_results.append({
                    "file_name": file_path,
                    "start_line": start,
                    "end_line": end,
                    "vulnerable": pickled_result,
                })


    file_path_messages = defaultdict(list)
    for res in pickled_results:
        if res["vulnerable"]:
            file_path_messages[res["file_name"]].append({
                "startLine": res["start_line"],
                "endLine": res["end_line"],
                "vulnerable": 1
            })

    calc = list(calculate_functions.values())
    if calc:
        pred_res = predict(calc)

        for res in pred_res:
            f_key = _get_function_key(res["file_name"], res["start_line"], res["end_line"])
            if f_key in calculate_functions:
                asd = calculate_functions[f_key]["hash"]
                _write_pickled_result(pickle_file=pickle_prefix / asd, prediction=res["is_vulnerable"])

            if res["is_vulnerable"]:
                file_path_messages[res["file_name"]].append({
                    "startLine": res["start_line"],
                    "endLine": res["end_line"],
                    "vulnerable": 1
                })

    for file_path, messages in file_path_messages.items():
        result_data.append({
            "filePath": file_path,
            "messages": messages
        })

    with open(input_file, 'w') as f:
        json.dump(result_data, f, indent=2)

    print("SUCCESS")


if __name__ == "__main__":
    args = _parse_args()
    # test with "python inference.py -i test.json -r test"
    main(input_file=args.input, run_id=args.run_id)
