import json
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

model_path = "Qwen/Qwen2.5-0.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

text2text_generator = pipeline("text-generation", model=model, tokenizer=tokenizer)


def _get_prompt(function_body):
    return [
        {"role": "system", "content": "You are a smart chatbot, answering only with yes or no"},
        {"role": "user", "content": f"""Does the function below contains any vulnerabilities?
```
{function_body}
```"""},
    ]


def predict(function_body):
    result = text2text_generator(_get_prompt(function_body), max_new_tokens=8, temperature=0.1)
    answer = result[0]['generated_text'][-1]["content"]
    prediction = int(answer.lower() == "yes")
    return prediction


if __name__ == "__main__":
    with open("test.json", 'r', encoding='utf-8') as f:
        test_function_body = json.load(f)[0]["messages"][0]["functionBody"]

    res = predict(test_function_body)
    print(res)
