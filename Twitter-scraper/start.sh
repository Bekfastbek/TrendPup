# Install Xvfb (if not already installed)
sudo apt-get update
sudo apt-get install -y xvfb

# Start Xvfb
Xvfb :99 -screen 0 1280x1024x24 &
export DISPLAY=:99

# Run the scraper
cd Twitter-scraper
python3 helix_scraper.py