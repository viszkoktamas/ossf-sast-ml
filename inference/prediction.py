import json
import random


def predict(function_body):
    random_number = random.randint(1, 100)
    return random_number > 50


if __name__ == "__main__":
    with open("test.json", 'r', encoding='utf-8') as f:
        test_function_body = json.load(f)[0]["messages"][0]["functionBody"]

    result = predict(test_function_body)
    print(result)
