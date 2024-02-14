from quart import Quart, jsonify, request
import json
import logging

import inference


logging.basicConfig(filename="log.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)


def main():
    app = Quart(__name__)
    i_model = inference.get_inference_models()
    t_model = inference.get_tokenizer_model()

    print(f" ----------------- {len(i_model)} models loaded")
    print(f" ----------------- CPU count: {inference.get_cpu_count()}")

    @app.post('/')
    async def work():
        try:
            data = await request.get_data()
            request_json = json.loads(data)
            input_file = request_json.get('input_file')
            if input_file:
                inference.main(input_file=input_file, inference_model=i_model, tokenizer_model=t_model, ensemble=True)

        except Exception as e:
            return jsonify("FAILURE - ", e)

        return jsonify("SUCCESS")

    app.run()


if __name__ == '__main__':
    main()
