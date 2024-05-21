from quart import Quart, jsonify, request
import json
import logging
import os

import inference

logging.basicConfig(filename="log.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)


def main():
    models_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ensemble_models')
    app = Quart(__name__)
    i_models = inference.get_inference_models(models_folder)
    t_model = inference.get_tokenizer_model()

    print(f" ----------------- {len(i_models)} models loaded")
    print(f" ----------------- CPU core count: {inference.get_cpu_count()}")

    @app.post('/')
    async def work():
        try:
            data = await request.get_data()
            request_json = json.loads(data)
            input_file = request_json.get('input_file')
            if input_file:
                inference.main(input_file=input_file, inference_models=i_models, tokenizer_model=t_model, run_id=models_folder)

        except Exception as e:
            return jsonify("FAILURE - ", e)

        return jsonify("SUCCESS")

    app.run()


if __name__ == '__main__':
    main()
