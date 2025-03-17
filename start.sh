#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    nc -z 0.0.0.0 $1 >/dev/null 2>&1
}

# Function to kill process using a port
kill_port() {
    if port_in_use $1; then
        echo "Port $1 is in use. Attempting to free it..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            lsof -ti tcp:$1 | xargs kill -9
        else
            # Linux
            fuser -k $1/tcp
        fi
    fi
}

# Check for required package managers
if ! command_exists pnpm; then
    echo "pnpm is not installed. Please install it first:"
    echo "npm install -g pnpm"
    exit 1
fi

# Kill any processes using our ports
kill_port 3000
kill_port 8080
kill_port 3001

echo "Starting services..."

# Create a new tmux session named "trendpup"
if command_exists tmux; then
    # Kill existing session if it exists
    tmux kill-session -t trendpup 2>/dev/null

    # Create new session
    tmux new-session -d -s trendpup

    # Start backend in first window
    # Explicitly set SERVER_PORT to 3001 to avoid conflicts
    # Make sure WebSocket server can start on 8080
    tmux send-keys -t trendpup:0 'cd agent1/eliza-starter && pnpm install && HOST=0.0.0.0 SERVER_PORT=3001 pnpm start --character="./characters/balance.character.json"' C-m
    
    # Wait a bit for the backend to start
    sleep 5

    # Create new window for frontend
    tmux new-window -t trendpup:1
    # Use production build to avoid any module resolution issues
    tmux send-keys -t trendpup:1 'cd frontend && pnpm install && pnpm build && PORT=3000 pnpm next start --port 3000 --hostname 0.0.0.0' C-m

    # Attach to the session
    tmux attach-session -t trendpup

else
    # If tmux is not available, use background processes
    echo "Starting services..."
    
    # Start backend with explicit port settings
    (cd agent1/eliza-starter && pnpm install && HOST=0.0.0.0 SERVER_PORT=3001 pnpm start --character="./characters/balance.character.json") &
    
    # Wait a bit for backend to start
    sleep 5
    
    # Start frontend
    (cd frontend && pnpm install && pnpm build && PORT=3000 pnpm next start --port 3000 --hostname 0.0.0.0) &
    
    # Wait for both processes
    wait
fi 