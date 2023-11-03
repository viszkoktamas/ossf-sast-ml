import os
import json
import argparse
import torch
import tensorflow as tf
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel
from keras import backend as K
from keras.layers import Lambda


def custom_f1(y_true, y_pred):
    def recall_m(y_true, y_pred):
        TP = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        Positives = K.sum(K.round(K.clip(y_true, 0, 1)))

        recall = TP / (Positives + K.epsilon())
        return recall

    def precision_m(y_true, y_pred):
        TP = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        Pred_Positives = K.sum(K.round(K.clip(y_pred, 0, 1)))

        precision = TP / (Pred_Positives + K.epsilon())
        return precision

    precision, recall = precision_m(y_true, y_pred), recall_m(y_true, y_pred)

    return 2 * ((precision * recall) / (precision + recall + K.epsilon()))


def embed_function(function_string):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
    model = AutoModel.from_pretrained("microsoft/codebert-base")
    model.to(device)
    code_tokens = tokenizer.tokenize(function_string)
    if len(code_tokens) > 510:
        code_tokens = code_tokens[0:510]

    tokens = [tokenizer.cls_token] + code_tokens + [tokenizer.sep_token]
    tokens_ids = tokenizer.convert_tokens_to_ids(tokens)
    context_embeddings = model(torch.tensor(tokens_ids)[None, :].to(device))[0][0][0]
    return context_embeddings.tolist()


def inference(embedding):
    dir_name = os.path.dirname(os.path.abspath(__file__))
    model = tf.keras.models.load_model(os.path.join(dir_name, 'models/model.h5'), custom_objects={"custom_f1": custom_f1})
    model.add(Lambda(lambda x: K.cast(K.argmax(x), dtype='float32'), name='y_pred'))
    return model.predict(embedding)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input json containing function data")
    args = parser.parse_args()
    with open(args.input, 'r') as f:
        function_data = json.load(f)

    result_data = []
    changed = False
    with tqdm(total=sum(sum(map(lambda a: len(a), file_data.values())) for file_data in function_data)) as pbar:
        for file_data in function_data:
            messages = []
            has_vulnerability = False
            functions = file_data.get("messages", [])
            for f in functions:
                function_body = f.get("functionBody")
                if not function_body:
                    pbar.update(1)
                    continue

                if "vulnerable" not in f:
                    vector = embed_function(function_body)
                    prediction = int(round(inference([vector])[0]))
                    f["vulnerable"] = prediction

                if f["vulnerable"] == 1:
                    messages.append(f)

                pbar.update(1)
                changed = True

            if messages:
                result_data.append({
                    "filePath": file_data.get("filePath", ""),
                    "messages": messages
                })

    if changed:
        with open(args.input, 'w') as f:
            json.dump(result_data, f)

    print("SUCCESS")
