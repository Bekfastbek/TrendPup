# Helix App Scraper

This script scrapes cryptocurrency data from Helix App (https://helixapp.com/spot/inj-usdt) for all pairs ending with "/INJ".

## Requirements

- Python 3.7+
- Playwright
- Xvfb (X Virtual Frame Buffer) for running headed browser on headless servers

## Setup

1. Install the required packages:
   ```
   pip install -r requirements_helix.txt
   ```

2. Install Playwright browsers:
   ```
   python -m playwright install
   ```

3. Install Xvfb (on Debian/Ubuntu):
   ```
   sudo apt-get update
   sudo apt-get install -y xvfb
   ```

## Usage

### With Virtual Display (for servers without a display)

1. Start Xvfb:
   ```
   Xvfb :99 -screen 0 1280x1024x24 &
   export DISPLAY=:99
   ```

2. Navigate to the Twitter-scraper directory and run the scraper:
   ```
   cd Twitter-scraper
   python helix_scraper.py
   ```

### On a system with a physical display

Simply navigate to the Twitter-scraper directory and run the script:
```
cd Twitter-scraper
python helix_scraper.py
```

The browser will open visibly and you'll be able to see the scraping process.

## Output

The script generates the following files in the Twitter-scraper directory:
- `helix_data.json`: Contains all scraped cryptocurrency data in JSON format
- `helix_scraper.log`: Log file with details about the scraping process
- `helix_screenshot.png`: Screenshot of the page for debugging
- `helix_page.html`: HTML content of the page for debugging (if initial extraction method fails)

## Data Structure

The output JSON has the following structure:
```json
{
  "data": [
    {
      "symbol": "BTC/INJ",
      "price": "123.45",
      "volume": "1.2M",
      "change_24h": "+1.23%",
      "timestamp": "2023-05-01T12:34:56.789Z"
    },
    ...
  ],
  "metadata": {
    "source": "https://helixapp.com/spot/inj-usdt",
    "timestamp": "2023-05-01T12:34:56.789Z",
    "count": 10
  }
}
``` 