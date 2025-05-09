#!/bin/bash

COMMAND_1="bash run_chat_completion_swarm_server.sh"
COMMAND_2="bash run_chat_completion_server.sh"

# Name of the tmux session.
SESSION="local_llama_example_session"

# Cleanup function to kill the tmux session.
cleanup() {
    echo "Cleaning up: Killing tmux session '$SESSION'."
    tmux kill-session -t "$SESSION" >/dev/null 2>&1
}

# Trap EXIT and common termination signals to ensure cleanup.
trap cleanup EXIT SIGINT SIGTERM

# Create a new tmux session in detached mode.
tmux new-session -d -s "$SESSION" || { echo "Failed to create tmux session."; exit 1; }

# In pane 0 (leftmost pane), run COMMAND_1.
tmux send-keys -t "$SESSION":0.0 "$COMMAND_1" C-m

# Split the window horizontally to create a second pane.
tmux split-window -h -t "$SESSION":0

# Optionally, equalize the layout across three panes.
tmux select-layout -t "$SESSION":0 even-horizontal

tmux send-keys -t "$SESSION":0.1 "$COMMAND_2" C-m

# Attach to the tmux session.
tmux attach-session -t "$SESSION"

# When you detach (Ctrl-b d) or exit tmux, the cleanup function will kill the session.
