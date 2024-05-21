import os
import random
import json
import numpy as np
import argparse
import hashlib
import re
from pathlib import Path
import torch
import tensorflow as tf
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel
from keras import backend as K
from keras.layers import Lambda

# set random values for reproducibility
seed_value = 1337
os.environ['PYTHONHASHSEED'] = str(seed_value)
random.seed(seed_value)
np.random.seed(seed_value)
tf.random.set_seed(seed_value)
tf.compat.v1.set_random_seed(seed_value)
session_conf = tf.compat.v1.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
sess = tf.compat.v1.Session(graph=tf.compat.v1.get_default_graph(), config=session_conf)
tf.compat.v1.keras.backend.set_session(sess)


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


def embed_function(model, function_string):
    tokenizer, device, tokenizer_model = model
    code_tokens = tokenizer.tokenize(function_string)
    if len(code_tokens) > 510:
        code_tokens = code_tokens[0:510]

    tokens = [tokenizer.cls_token] + code_tokens + [tokenizer.sep_token]
    tokens_ids = tokenizer.convert_tokens_to_ids(tokens)
    context_embeddings = tokenizer_model(torch.tensor(tokens_ids)[None, :].to(device))[0][0][0]
    return context_embeddings.tolist()


def get_tokenizer_model():
    tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModel.from_pretrained("microsoft/codebert-base")
    model.to(device)

    return tokenizer, device, model


def _get_inference_model(model_path=None):
    if not model_path:
        dir_name = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(dir_name, 'models/model.h5')

    model = tf.keras.models.load_model(model_path, custom_objects={"custom_f1": custom_f1})
    model.add(Lambda(lambda x: K.cast(K.argmax(x), dtype='float32'), name='y_pred'))
    return model


def get_inference_models(dir_name=None):
    if not dir_name:
        dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ensemble_models')

    models = []
    for model_file in [os.path.join(dir_name, f) for f in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, f))]:
        models.append(_get_inference_model(model_path=model_file))

    return models


def inference(models, embedding):
    model_predictions = [m.predict(embedding)[0] for m in models]
    return int(round(sum(model_predictions)/len(model_predictions)))


def file_name_to_pickle_prefix(file_name, run_id):
    pickle_prefix = Path(os.path.dirname(os.path.abspath(__file__))) / 'cache' / run_id
    file_name = re.sub(r"[-.]", "_", file_name)
    file_name_parts = file_name.split('sources')[-1].split(os.path.sep)
    while file_name_parts:
        part = file_name_parts.pop()
        if part:
            pickle_prefix /= part

    return pickle_prefix


def load_pickled_result(pickle_file):
    try:
        if pickle_file.exists():
            with open(pickle_file, 'r', encoding='utf-8') as f:
                result = int(f.read())
                return result

    except Exception as e:
        print(f"Error loading pickled result {pickle_file}: {e}")

    return None


def write_pickled_result(pickle_file, prediction):
    pickle_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pickle_file, 'w', encoding='utf-8') as f:
        f.write(str(prediction))


def interval_contains(a_start, a_end, b_start, b_end):
    return a_start <= b_start and a_end >= b_end


def main(input_file, inference_models, tokenizer_model, run_id=None):
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

    result_data = []
    with tqdm(total=sum(len(file_data["messages"]) for file_data in function_data)) as pbar:
        for file_data in function_data:
            pickle_prefix = file_name_to_pickle_prefix(file_data.get("filePath", ''), run_id or 'run_1')
            messages_map = {}
            functions = file_data.get("messages", [])
            for f in functions:
                start = f.get("startLine", 0)
                end = f.get("endLine", 0)
                function_body = f.get("functionBody")
                if not function_body:
                    pbar.update(1)
                    continue

                function_body_hash = hashlib.sha512(function_body.encode('utf-8')).hexdigest()
                pickle_file = pickle_prefix / function_body_hash
                pickled_result = load_pickled_result(pickle_file=pickle_file)
                if pickled_result is not None:
                    f["vulnerable"] = pickled_result

                else:
                    vector = embed_function(model=tokenizer_model, function_string=function_body)
                    prediction = inference(models=inference_models, embedding=[vector])
                    f["vulnerable"] = prediction
                    write_pickled_result(pickle_file=pickle_file, prediction=prediction)

                if f["vulnerable"]:
                    found = False
                    for m_start, m_data in messages_map.items():
                        m_end = m_data["endLine"]
                        if interval_contains(m_start, m_end, start, end):
                            found = True
                            break

                        if interval_contains(start, end, m_start, m_end):
                            messages_map.pop(m_start)

                    if not found:
                        messages_map[start] = f

                pbar.update(1)

            if messages_map:
                result_data.append({
                    "filePath": file_data.get("filePath", ""),
                    "messages": list(messages_map.values())
                })

    with open(input_file, 'w') as f:
        json.dump(result_data, f, indent=2)

    print("SUCCESS")


def get_cpu_count():
    return torch.multiprocessing.cpu_count()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input json containing function data")
    parser.add_argument("-m", "--models-dir", help="path to model files directory")
    parser.add_argument("-r", "--run_id", help="run id")
    return parser.parse_args()


if __name__ == "__main__":
    print(" ----------------- CPU core count:", get_cpu_count())
    args = parse_args()
    i_models = get_inference_models(dir_name=args.models_dir)
    t_model = get_tokenizer_model()
    main(input_file=args.input, inference_models=i_models, tokenizer_model=t_model, run_id=args.run_id)
