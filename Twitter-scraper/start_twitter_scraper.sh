#!/bin/bash

# Change to the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create screenshots directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/screenshots"

# Check if Xvfb is installed
if ! command -v Xvfb &> /dev/null; then
    echo "Xvfb is not installed. Installing now..."
    sudo apt-get update
    sudo apt-get install -y xvfb
fi

# Check if we already have an Xvfb instance running
if pgrep -x "Xvfb" > /dev/null; then
    echo "Xvfb is already running."
else
    echo "Starting Xvfb..."
    # Start Xvfb on display :99 with screen resolution 1280x800x24
    Xvfb :99 -screen 0 1280x800x24 -ac &
    XVFB_PID=$!
    
    # Wait for Xvfb to initialize
    sleep 2
    
    echo "Xvfb started with PID: $XVFB_PID"
fi

# Set the DISPLAY environment variable to the virtual display
export DISPLAY=:99

echo "Using virtual display: $DISPLAY"

# Ensure the environment is active if using a virtualenv
# Uncomment if using a virtual environment
# source venv/bin/activate

# Install or update dependencies
pip3 install -r requirements.txt

echo "Starting Twitter scraper..."
# Run the Twitter scraper
python3 twitter_scraper.py

# Cleanup - kill Xvfb process if we started it
if [ -n "$XVFB_PID" ]; then
    echo "Stopping Xvfb..."
    kill $XVFB_PID
fi

# Inform about output locations
echo "Twitter data saved to: $SCRIPT_DIR/twitter_coin_data.json"
echo "Analysis saved to: $SCRIPT_DIR/coin_investment_analysis.json"
echo "Screenshots saved to: $SCRIPT_DIR/screenshots" 