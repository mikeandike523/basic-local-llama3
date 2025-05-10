import json
from flask import Flask, request, jsonify
import os
import requests
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app)

ports_dir = os.path.realpath("ports")

@app.route('/completion', methods=['POST'])
def process():
    data = request.get_json()

    files = list(filter(lambda x: x.endswith(".txt"), os.listdir(ports_dir)))
    status = {}

    for file in files:
        port_number = int(os.path.splitext(file)[0])
        file_path = os.path.join(ports_dir, file)
        
        with open(file_path, "r") as fl:
            is_busy = fl.read().strip().lower() == "true"
            status[port_number] = is_busy

    print("Status of ports:", status)

    available_port = next((port for port, busy in status.items() if not busy), None)

    if available_port is None:
        return jsonify({"error": "All LLM servers are busy."}), 503

    try:
        response = requests.post(
            f"http://localhost:{available_port}/completion",
            json=data
        )
        response.raise_for_status()

        response_json = response.json()

        print(json.dumps(response_json, indent=2))

        print(f"Served by: {response_json["served_by"]}")

        return jsonify(response_json["result"])

    except Exception as e:
        traceback.print_exc()
        print("Error forwarding request:", str(e))
        return jsonify("Failed to reach LLM server."), 500

if __name__ == '__main__':
    app.run(threaded=True, debug=False, port=5000)
