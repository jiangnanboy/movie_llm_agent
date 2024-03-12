import os

from transformers import (
    AutoConfig,
    AutoModel,
    AutoTokenizer,
)

pwd_path = os.path.abspath(os.path.dirname(__file__))
model_name_or_path = os.path.join(pwd_path, "chatglm-6b")

device_id = os.getenv("DEVICE", "0")

config = AutoConfig.from_pretrained(model_name_or_path, trust_remote_code=True)
model = AutoModel.from_pretrained(model_name_or_path, config=config, trust_remote_code=True).half().cuda(int(device_id))
tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True,use_fast=True)
model.eval()

import json

from flask import Flask
from flask import request
#from flask_siwadoc import SiwaDoc
from gevent import pywsgi

app = Flask(__name__)

#siwa = SiwaDoc(app)

@app.route("/", methods=["POST", "GET"])
def root():
    """root
    """
    return "Welcome to chatglm movie llm agent"

@app.route("/chat", methods=["POST"])
def chat():
    """chat
    """
    data_seq = request.get_data()
    data_dict = json.loads(data_seq)
    human_input = data_dict["prompt"]
    history = data_dict['history']
    response, _ = model.chat(tokenizer, human_input, history=history)
    result_dict = {
        "response": response
    }
    result_seq = json.dumps(result_dict, ensure_ascii=False)
    return result_seq

if __name__ == "__main__":
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()
    #app.run(host="0.0.0.0", port=8595, debug=False)