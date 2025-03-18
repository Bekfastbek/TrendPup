# Twitter Scraper

A tool to scrape Twitter for memecoin mentions and analyze the content using Google's Gemini AI.

## Authentication

This scraper uses a cookie-based authentication method for Twitter and requires a Gemini API key for analysis.

### Twitter Authentication

1. Log in to Twitter/X in a regular browser
2. Install a cookie export extension:
   - For Chrome: [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
   - For Firefox: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

3. Navigate to x.com (not twitter.com)
4. Open the Cookie-Editor extension
5. Click "Export" in the bottom right (this copies cookies to clipboard)
6. Create a file named `twitter_cookies.json` in the same directory as the scraper
7. Paste the copied cookies and save the file

### Gemini API Setup

The analyzer uses Google's Gemini API to analyze tweets. To set it up:

1. Get a Gemini API key from https://aistudio.google.com/app/apikey
2. Edit the `.env` file and replace `your_api_key_here` with your actual Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Running the Pipeline

1. Make sure you have all dependencies installed:
   ```
   pip install playwright pandas watchdog python-dotenv google-generativeai
   playwright install
   ```

2. Run the integrated pipeline:
   ```
   python3 twitter_pipeline.py
   ```

This will:
- Start the Twitter scraper to collect data
- Monitor for changes to the data file
- Automatically run the Gemini analyzer whenever new data is collected

## Notes

- Cookies typically expire after a certain period, so you may need to refresh them periodically
- The pipeline handles all components (scraper, file watching, analysis) in a single integrated process
- Press Ctrl+C to gracefully shut down the pipeline 