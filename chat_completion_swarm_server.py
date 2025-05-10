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

import sys
from typing import List, Optional
import os
import socket
import json
import time
import threading
import traceback
import json
from math import isfinite

import fire
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS


# Import your model and related classes.
from llama_models.datatypes import RawMessage
from llama_models.llama3.generation import Llama
from termcolor import colored
from token_counter import TokenCounter
from llama_models.datatypes import StopReason


MAX_SEQ_LEN = 8192
MAX_BATCH_SIZE = 1


DEFAULT_MAX_TOKENS = None
DEFAULT_TOP_P = 0.9
DEFAULT_TEMPERATURE = 0.5


generator = None
global_port = None
global_max_seq_len = None
port_status_file = None
global_ckpt_dir = None
global_gpu_id = None

app = Flask(__name__)
CORS(app)

RESERVED_PORTS = [22, 80, 443, 3000, 5000]


class OutOfTokensError(Exception):

    HTTP_STATUS = 429

    def __init__(
        self, budget: int, conversation_length: int, gen_length: Optional[int] = None
    ):
        message = f"""
Out of tokens.

Budget={budget} tokens.

Be aware that the token limit applies to both conversation and response.

Unlimited generation can lead to unpredictable budget excession.
It is recommeded to have some explicit limit, even if large.

Conversation Length={conversation_length}

Generation Length={"Unlimited" if gen_length is None else gen_length}

""".strip()

        super().__init__(message)
        self.budget = budget
        self.conversation_length = conversation_length
        self.gen_length = gen_length

    def to_json(self):
        return {
            "name": "OutOfTokensError",
            "message": str(self),
            "budget": self.budget,
            "conversation_length": self.conversation_length,
            "gen_length": self.gen_length,
        }


class InvalidRequestError(Exception):
    HTTP_STATUS = 400

    def to_json(self):
        return {"name": "InvalidRequestError", "message": str(self)}

    @classmethod
    def combine(cls, errors: List["InvalidRequestError"]):
        return InvalidRequestError("\n\n".join([str(err) for err in errors]))


class InvalidResponseError(Exception):
    HTTP_STATUS = 500

    def to_json(self):
        return {"name": "InvalidResponseError", "message": str(self)}

    @classmethod
    def combine(cls, errors: List["InvalidResponseError"]):
        return InvalidResponseError("\n\n".join([str(err) for err in errors]))


class UnknownServerError(Exception):

    HTTP_STATUS = 500

    def __init__(self, err: Exception):
        super().__init__(str(err))

    def to_json(self):
        return {"name": "UnknownServerError", "message": str(self)}


def init_model(ckpt_dir: str, max_seq_len: int, max_batch_size: int, gpu_id: int):
    """Initialize the Llama model if not already built."""
    global generator, global_ckpt_dir, global_max_seq_len
    if generator is None:
        generator = Llama.build(
            ckpt_dir=ckpt_dir,
            max_seq_len=max_seq_len,
            max_batch_size=max_batch_size,
            device=f"cuda:{gpu_id}",
        )
        print("Model initialized.")

    return generator


def find_available_port():
    """Let the OS assign an available port by binding to port 0."""

    available_port = None
    while available_port is None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            available_port = int(s.getsockname()[1])
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
    global generator, global_port, global_max_seq_len
    # Mark this worker as busy
    write_port_status(global_port, busy=True)
    try:
        data = request.get_json(silent=True) or None

        if data is None:
            raise InvalidRequestError("Missing request body.")

        if not isinstance(data, dict):
            raise InvalidRequestError("Request json must be an object")

        temperature = data.get("temperature", DEFAULT_TEMPERATURE)
        top_p = data.get("top_p", DEFAULT_TOP_P)
        max_gen_len = data.get("max_tokens", DEFAULT_MAX_TOKENS)
        messages = data.get("messages", None)

            

        request_validation_errors = []

        if messages is None:
            request_validation_errors.append(InvalidRequestError("Missing or null `messages` field."))
        else:
            if not isinstance(messages, list):
                request_validation_errors.append(InvalidRequestError("Messages must be an array."))
            else:
                ... # todo: rest of validaiton logic for message list

        if not isinstance(temperature, (float, int)):
            request_validation_errors.append(
                InvalidRequestError(f"Invalid temperature: {temperature}")
            )
        else:
            temperature = float(temperature)

        if not isfinite(temperature) or temperature <= 0.0 or temperature > 1.0:
            request_validation_errors.append(
                InvalidRequestError(
                    f"Invalid temperature: {temperature}. Must be between 0.0 and 1.0."
                )
            )

        if not isinstance(top_p, (float, int)):
            request_validation_errors.append(InvalidRequestError(f"Invalid top_p: {top_p}"))
        else:
            top_p = float(top_p)

        if not isfinite(top_p) or top_p <= 0.0 or top_p > 1.0:
            request_validation_errors.append(
                InvalidRequestError(
                    f"Invalid top_p: {top_p}. Must be between 0.0 and 1.0."
                )
            )
        if max_gen_len is not None:
            if not isinstance(max_gen_len, int):
                request_validation_errors.append(
                    InvalidRequestError(f"Invalid max generation length: {max_gen_len}")
                )
            else:
                if not isfinite(max_gen_len) or max_gen_len <= 0:
                    request_validation_errors.append(
                        InvalidRequestError(
                            f"Invalid max generation length: {max_gen_len}. Must be >= 1"
                        )
                    )

        if request_validation_errors:
            raise InvalidRequestError.combine(request_validation_errors)

        messages = [RawMessage(role=m["role"], content=m["content"]) for m in messages]

        conversation_token_count = TokenCounter(global_max_seq_len).count(messages)

        result = generator.chat_completion(
            messages,
            max_gen_len=max_gen_len,
            temperature=temperature,
            top_p=top_p,
        )

        if result.generation.stop_reason == StopReason.out_of_tokens:
            raise OutOfTokensError(
                global_max_seq_len, conversation_token_count, max_gen_len
            )

        output_data = {
            "role": result.generation.role.strip(),
            "content": result.generation.content.strip(),
        }

        response_validation_errors = []

        if not output_data["role"]:
            response_validation_errors.append(
                InvalidResponseError("Llama response missing 'role' field.")
            )

        if not output_data["role"] in ("system", "user", "assistant", "tool"):
            response_validation_errors.append(
                InvalidResponseError(
                    f"Llama response has invalid role: {output_data["role"]}"
                )
            )

        if not output_data["content"]:
            response_validation_errors.append(
                InvalidResponseError(f"Empty Llama response content.")
            )

        if response_validation_errors:
            raise InvalidResponseError.combine(response_validation_errors)

        response = {"served_by": global_port, "result": output_data}
        write_port_status(global_port, busy=False)

        return jsonify(response)
    except OutOfTokensError as e:
        write_port_status(global_port, busy=False)
        sys.stderr.write(
            "\n\n"
            + colored(
                f"""
OutOfTokensError in swarm server (gpu_id={global_gpu_id}, port={global_port}):

{str(e)}

""".strip()  # traceback not needed for handled error case
                + "\n\n"
            ),
            "red",
        )
        return jsonify(e.to_json()), OutOfTokensError.HTTP_STATUS
    except InvalidResponseError as e:
        write_port_status(global_port, busy=False)
        sys.stderr.write(
            "\n\n"
            + colored(
                f"""
InvalidResponseError in swarm server (gpu_id={global_gpu_id}, port={global_port}):

{str(e)}

""".strip()  # traceback not needed for handled error case
                + "\n\n"
            ),
            "red",
        )
        return jsonify(e.to_json()), InvalidResponseError.HTTP_STATUS
    except Exception as e:
        tb_str = traceback.format_exc()
        sys.stderr.write(
            "\n\n"
            + colored(
                f"""
Unknown error in swarm server (gpu_id={global_gpu_id}, port={global_port}):

{str(e)}

Traceback:

{tb_str}

""".strip()
                + "\n\n"
            ),
            "red",
        )
        write_port_status(global_port, busy=False)
        return jsonify(UnknownServerError(e).to_json()), UnknownServerError.HTTP_STATUS


def serve(
    ckpt_dir: str,
    *,
    max_seq_len: int = MAX_SEQ_LEN,
    max_batch_size: int = MAX_BATCH_SIZE,
    gpu_id: int = 0,  # we run a unique process for each graphics card, i.e. one model instance per card.
    # Distributing tensors over multiple cards is not supported in llama at ths time
    host: str = "127.0.0.1",
):
    """
    Launch a Flask worker server on an available port.
    This function is intended to be launched by torchrun.
    """
    global global_port, port_status_file, global_ckpt_dir
    global global_max_seq_len, global_gpu_id

    global_port = find_available_port()
    port_status_file = write_port_status(global_port, busy=False)
    global_ckpt_dir = ckpt_dir
    global_max_seq_len = max_seq_len
    global_gpu_id = gpu_id

    init_model(ckpt_dir, max_seq_len, max_batch_size, gpu_id)

    print(f"Swarm server running on {host}:{global_port}")
    app.run(host=host, port=global_port, threaded=False, debug=False)


def main():
    fire.Fire(serve)


if __name__ == "__main__":
    main()
