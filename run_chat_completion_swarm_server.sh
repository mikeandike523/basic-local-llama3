#!/bin/bash

rm -rf ports

source "$HOME/.bashrc"
source "$CONDA_PROFILE_SCRIPT" && conda activate base
conda activate llm-flatland-env

CHECKPOINT_DIR="/home/adam-sohnen/.cache/huggingface/hub/models--meta-llama--Llama-3.2-3B-Instruct/snapshots/0cb88a4f764b7a12671c53f0838cd831a0843b95/original"

echo ""
echo "Loading..."
echo ""


REPO_ROOT="$(git rev-parse --show-toplevel)"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$REPO_ROOT"

torchrun --nnodes=1 chat_completion_swarm_server.py "$CHECKPOINT_DIR" 

conda deactivate
conda deactivate