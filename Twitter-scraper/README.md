# Twitter Scraper

A tool to scrape Twitter for memecoin mentions and other content.

## Authentication

This scraper now uses a cookie-based authentication method only. The automated login feature has been removed to avoid detection.

### How to Set Up Cookie Authentication:

1. Log in to Twitter/X in a regular browser
2. Install a cookie export extension:
   - For Chrome: [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
   - For Firefox: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

3. Navigate to x.com (not twitter.com)
4. Open the Cookie-Editor extension
5. Click "Export" in the bottom right (this copies cookies to clipboard)
6. Create a file named `twitter_cookies.json` in the same directory as the scraper
7. Paste the copied cookies and save the file

## Running the Scraper

1. Make sure you have all dependencies installed:
   ```
   pip install playwright pandas
   playwright install
   ```

2. Run the scraper:
   ```
   ./run_scraper.sh
   ```

## Notes

- Cookies typically expire after a certain period, so you may need to refresh them periodically
- The scraper will automatically attempt to use your cookies for authentication
- If authentication fails, you'll need to export fresh cookies from your browser
- Make sure to export cookies from x.com (not twitter.com) 