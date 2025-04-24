source "$HOME/.bashrc"
source "$CONDA_PROFILE_SCRIPT" && conda activate base
conda activate llm-flatland-env
python chat_completion_server.py
conda deactivate
conda deactivate