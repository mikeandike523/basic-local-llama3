#!/usr/bin/env python
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# top-level folder for each specific model found within the models/ directory at
# the top-level of this source tree.
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# This software may be used and distributed in accordance with the terms of the Llama 3 Community License Agreement.

from typing import Optional
import os
import socket
import json
import time
import threading

import fire
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS


# Import your model and related classes.
from llama_models.datatypes import RawMessage
from llama_models.llama3.generation import Llama


MAX_SEQ_LEN=8192
MAX_BATCH_SIZE=1


DEFAULT_MAX_TOKENS = None
DEFAULT_TOP_P = 0.9
DEFAULT_TEMPERATURE = 0.5






# Global variables for the worker
generator = None
global_port = None
port_status_file = None

app = Flask(__name__)
CORS(app)

RESERVED_PORTS=[22, 80, 443, 3000, 5000]

def init_model(ckpt_dir: str, max_seq_len: int, max_batch_size: int):
    """Initialize the Llama model if not already built."""
    global generator
    if generator is None:
        generator = Llama.build(
            ckpt_dir=ckpt_dir,
            max_seq_len=max_seq_len,
            max_batch_size=max_batch_size,
            device="cuda"
        )
        print("Model initialized.")
    return generator

def find_available_port():
    """Let the OS assign an available port by binding to port 0."""

    available_port = None
    while available_port is None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            available_port=int(s.getsockname()[1])
            if available_port in RESERVED_PORTS:
                available_port = None
    return available_port

def write_port_status(port: int, busy: bool, port_dir: str = "ports"):
    """Write the busy status to a file named <port>.txt in the given directory."""
    os.makedirs(port_dir, exist_ok=True)
    status_file = os.path.join(port_dir, f"{port}.txt")
    with open(status_file, "w") as f:
        f.write("true" if busy else "false")
    return status_file

@app.route("/completion", methods=["POST"])
def completions():
    """Endpoint to perform chat completion.
       Expects a JSON payload with keys:
         - in_file: path to the input file
         - out_file: path to the output file
         - temperature, top_p, max_gen_len (optional)
    """
    global generator, global_port
    # Mark this worker as busy
    write_port_status(global_port, busy=True)
    try:
        data = request.get_json()
        temperature = data.get("temperature", DEFAULT_TEMPERATURE)
        top_p = data.get("top_p", DEFAULT_TOP_P)
        max_gen_len = data.get("max_tokens", DEFAULT_MAX_TOKENS)
        messages = data.get("messages", [])

        messages = [RawMessage(role=m["role"], content=m["content"]) for m in messages]
        
        # Run the chat completion
        result = generator.chat_completion(
            messages,
            max_gen_len=max_gen_len,
            temperature=temperature,
            top_p=top_p,
        )
        
        output_data = {
            "role": result.generation.role,
            "content": result.generation.content,
        }

        response = {
            "served_by":global_port,
            "result": output_data
        }
        write_port_status(global_port, busy=False)
        return jsonify(response)
    except Exception as e:
        write_port_status(global_port, busy=False)
        return jsonify(str(e), 500)

def serve(ckpt_dir: str,
          max_seq_len: int = MAX_SEQ_LEN,
          max_batch_size: int = MAX_BATCH_SIZE,
          host: str = "127.0.0.1"):
    """
    Launch a Flask worker server on an available port.
    This function is intended to be launched by torchrun.
    """
    global global_port, port_status_file
    init_model(ckpt_dir, max_seq_len, max_batch_size)
    global_port = find_available_port()
    port_status_file = write_port_status(global_port, busy=False)
    print(f"Worker server running on {host}:{global_port} with status file: {port_status_file}")
    # Run Flask in threaded mode
    app.run(host=host, port=global_port, threaded=False, debug=False)

def main():
    fire.Fire(serve)

if __name__ == "__main__":
    main()
