#!/bin/bash

# Kill any process running on port 8000
kill_server() {
    pid=$(lsof -ti:8000)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port 8000..."
        kill -9 $pid
    fi
}

# Start the server with the specified mode
start_server() {
    local mode=$1
    local debug_flag=""
    
    if [ "$mode" = "debug" ]; then
        debug_flag="--log-level debug"
    fi
    
    echo "Starting server in $mode mode..."
    ./venv/bin/uvicorn backend.main:app --reload --port 8000 $debug_flag
}

# Main execution
MODE=${1:-"normal"}  # Default to normal mode if no argument provided
kill_server
start_server $MODE
