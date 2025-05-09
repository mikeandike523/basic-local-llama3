#!/bin/bash



rm -rf ports

conda_base() {
    eval "$("$HOME/anaconda3/bin/conda" shell.bash hook)"
}
conda_base
conda activate basic-local-llama3-env
dn="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$dn"
CHECKPOINT_DIR="$HOME/models/Llama-3.2-3B-Instruct/original"

echo ""
echo "Loading..."
echo ""

torchrun --nnodes=1 chat_completion_swarm_server.py "$CHECKPOINT_DIR" 

conda deactivate
conda deactivate