#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required package managers
if ! command_exists pnpm; then
    echo "pnpm is not installed. Installing globally..."
    npm install -g pnpm
fi

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
    tmux send-keys -t trendpup:0 'cd agent && pnpm install && HOST=0.0.0.0 SERVER_PORT=3001 pnpm start --character="./characters/balance.character.json"' C-m
    
    # Wait a bit for the backend to start
    sleep 5

    # Create new window for frontend
    tmux new-window -t trendpup:1
    # Start Next.js app using standard command
    tmux send-keys -t trendpup:1 'cd frontend && pnpm install && pnpm build && pnpm start' C-m

    # Attach to the session
    tmux attach-session -t trendpup

else
    # If tmux is not available, use background processes
    echo "Starting services..."
    
    # Start backend with explicit port settings
    (cd agent && pnpm install && HOST=0.0.0.0 SERVER_PORT=3001 pnpm start --character="./characters/balance.character.json") &
    
    # Wait a bit for backend to start
    sleep 5
    
    # Start frontend with standard Next.js command
    (cd frontend && pnpm install && pnpm build && pnpm start) &
    
    # Wait for both processes
    wait
fi 