#!/bin/bash

# Scheduled scraper script that runs both scrapers at hourly intervals
# Helix scraper runs first, followed by Twitter scraper

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to run helix scraper
run_helix_scraper() {
    echo "$(date): Starting Helix scraper..."
    
    # Check if we already have a display
    if [ -z "$DISPLAY" ]; then
        # Start Xvfb
        export DISPLAY=:99
        echo "Starting Xvfb on display $DISPLAY"
        Xvfb $DISPLAY -screen 0 1280x800x24 &
        XVFB_PID=$!
        
        # Wait for Xvfb to start
        sleep 2
        
        # Check if Xvfb is running
        if ! ps -p $XVFB_PID > /dev/null; then
            echo "Error: Xvfb failed to start"
            return 1
        fi
        
        echo "Xvfb started successfully with PID $XVFB_PID"
    fi
    
    # Get current date-time for log file names
    DATETIME=$(date +"%Y%m%d_%H%M%S")
    HELIX_LOG_FILE="$LOG_DIR/helix_scraper_$DATETIME.log"
    
    # Run the Helix scraper
    cd "$SCRIPT_DIR"
    python3 helix_scraper.py 2>&1 | tee -a "$HELIX_LOG_FILE"
    
    # Check if the scraper was successful
    if [ -f "$SCRIPT_DIR/helix_data.json" ]; then
        echo "$(date): Helix scraper completed successfully"
        return 0
    else
        echo "$(date): Helix scraper failed - data file not found"
        return 1
    fi
}

# Function to run Twitter scraper
run_twitter_scraper() {
    echo "$(date): Starting Twitter scraper..."
    
    # Check if we already have a display
    if [ -z "$DISPLAY" ]; then
        # Start Xvfb
        export DISPLAY=:99
        echo "Starting Xvfb on display $DISPLAY"
        Xvfb $DISPLAY -screen 0 1280x800x24 &
        XVFB_PID=$!
        
        # Wait for Xvfb to start
        sleep 2
        
        # Check if Xvfb is running
        if ! ps -p $XVFB_PID > /dev/null; then
            echo "Error: Xvfb failed to start"
            return 1
        fi
        
        echo "Xvfb started successfully with PID $XVFB_PID"
    fi
    
    # Get current date-time for log file names
    DATETIME=$(date +"%Y%m%d_%H%M%S")
    TWITTER_LOG_FILE="$LOG_DIR/twitter_scraper_$DATETIME.log"
    
    # Run the Twitter scraper
    cd "$SCRIPT_DIR"
    python3 twitter_scraper.py 2>&1 | tee -a "$TWITTER_LOG_FILE"
    
    # Check if the scraper was successful
    if [ -f "$SCRIPT_DIR/coin_investment_analysis.json" ]; then
        echo "$(date): Twitter scraper completed successfully"
        return 0
    else
        echo "$(date): Twitter scraper failed - analysis file not found"
        return 1
    fi
}

# Main loop - run forever until interrupted
run_scrapers() {
    echo "$(date): Starting scheduled scraper run..."
    
    # First run the Helix scraper
    run_helix_scraper
    HELIX_RESULT=$?
    
    # Only run the Twitter scraper if Helix was successful
    if [ $HELIX_RESULT -eq 0 ]; then
        # Wait a moment for files to be properly written
        sleep 5
        
        # Run the Twitter scraper
        run_twitter_scraper
        TWITTER_RESULT=$?
        
        if [ $TWITTER_RESULT -eq 0 ]; then
            echo "$(date): Scheduled run completed successfully"
        else
            echo "$(date): Twitter scraper failed in scheduled run"
        fi
    else
        echo "$(date): Helix scraper failed, skipping Twitter scraper"
    fi
    
    echo "$(date): Scheduled run finished, waiting for next interval"
}

# Set up cron job if requested
if [ "$1" == "--setup-cron" ]; then
    # Remove any existing cron job
    (crontab -l 2>/dev/null | grep -v "scheduled_scraper.sh") | crontab -
    
    # Add new cron job to run at the start of every hour
    (crontab -l 2>/dev/null; echo "0 * * * * $SCRIPT_DIR/scheduled_scraper.sh --once >> $LOG_DIR/cron_$(date +\%Y\%m\%d).log 2>&1") | crontab -
    
    echo "Cron job set up to run scrapers at the start of every hour"
    exit 0
fi

# Start Xvfb for the entire script run
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

# Check for command line arguments
if [ "$1" == "--once" ]; then
    # Run once and exit
    run_scrapers
    exit 0
fi

# Main scheduling loop
echo "Starting hourly scraper schedule at $(date)"
echo "The scrapers will run immediately and then at the start of every hour"

# Run immediately on startup
run_scrapers

while true; do
    # Calculate time until next hour
    # Get current minutes and seconds
    MINUTES=$(date +%M)
    SECONDS=$(date +%S)
    
    # Calculate seconds until next hour (3600 seconds in an hour)
    SLEEP_SECONDS=$((3600 - MINUTES*60 - SECONDS))
    
    # If we're very close to the next hour, add some buffer time
    if [ $SLEEP_SECONDS -lt 60 ]; then
        SLEEP_SECONDS=$((SLEEP_SECONDS + 60))
    fi
    
    echo "$(date): Sleeping for $SLEEP_SECONDS seconds until next run"
    sleep $SLEEP_SECONDS
    
    # Run the scrapers
    run_scrapers
done 