#!/bin/bash

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create screenshots directory if it doesn't exist
# Screenshots are now disabled to save storage space
# mkdir -p "$SCRIPT_DIR/screenshots"

# Start Xvfb
export DISPLAY=:99
echo "Starting Xvfb on display $DISPLAY"
Xvfb $DISPLAY -screen 0 1280x800x24 &
XVFB_PID=$!

# Ensure we kill Xvfb on script exit
trap "echo 'Cleaning up processes...'; kill $XVFB_PID 2>/dev/null; echo 'Done.'" EXIT

# Wait for Xvfb to start
sleep 2

# Check if Xvfb is running
if ! ps -p $XVFB_PID > /dev/null; then
    echo "Error: Xvfb failed to start"
    exit 1
fi

echo "Xvfb started successfully with PID $XVFB_PID"

# Create a log directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Get current date-time for log file names
DATETIME=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$SCRIPT_DIR/logs/twitter_scraper_$DATETIME.log"

# Display settings
echo "Display settings:"
echo "----------------"
echo "DISPLAY=$DISPLAY"

# Run Xrandr to verify display configuration
if command -v xrandr >/dev/null 2>&1; then
    echo "Display information from xrandr:"
    XAUTHORITY=/root/.Xauthority xrandr || echo "xrandr command failed"
else
    echo "xrandr command not available"
fi

# Activate virtualenv if it exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "Activating virtual environment"
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Run the Python script
echo "Starting Twitter scraper..."
cd "$SCRIPT_DIR"
python3 twitter_scraper.py 2>&1 | tee -a "$LOG_FILE"

# Print completion message
echo "Twitter scraper completed"
echo "Log saved to: $LOG_FILE"
# Screenshots are now disabled to save storage space
# echo "Screenshots saved to: $SCRIPT_DIR/screenshots" 