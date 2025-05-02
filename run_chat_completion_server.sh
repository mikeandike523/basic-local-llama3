#!/bin/bash


conda_base() {
    eval "$("$HOME/anaconda3/bin/conda" shell.bash hook)"
}
conda_base
conda activate basic-local-llama3-env
dn="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$dn"
python chat_completion_server.py
conda deactivate
conda deactivate