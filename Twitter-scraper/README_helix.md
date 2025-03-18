# Helix Protocol Scraper

A specialized web scraper designed to extract cryptocurrency data from the Helix App, focusing on trading pairs ending with /INJ.

## Features

### Basic Scraping
- Extracts a list of all cryptocurrency pairs with INJ
- Captures basic market information (symbol, price, volume, 24h change)

### Enhanced Detailed Scraping (New)
- Navigates to each individual coin's page
- Clicks on the Info tab to access detailed market information
- Extracts comprehensive data including:
  - Market ID (contract address)
  - Market Name
  - Tick Size
  - Min. Limit Order Size
  - 24h High/Low prices
  - Direct link to the coin's Helix page

## Output Files

The scraper generates two main data files:
1. `helix_data.json` - Basic list of all cryptocurrency pairs with INJ
2. `helix_detailed_data.json` - Comprehensive data including Market IDs and Helix links

## Debugging & Monitoring

The scraper takes screenshots at various stages to help with debugging:
- Initial page load
- After clicking All Markets
- After searching for /INJ pairs
- Individual coin pages
- Info tabs for each coin
- Error states (when they occur)

All activity is logged to `helix_scraper.log` for monitoring and troubleshooting.

## Usage

```bash
python helix_scraper.py
```

## Requirements

See `requirements_helix.txt` for the necessary dependencies. The scraper uses Playwright for browser automation.

## Data Structure

The enhanced detailed data JSON file (`helix_detailed_data.json`) follows this structure:

```json
{
  "data": [
    {
      "symbol": "HINJ/INJ",
      "market_id": "0x1b1e062b3306f26ae3af3c354a10c1cf38b00dcb42917f038ba3fc14978b1dd8",
      "market_name": "hINJ/INJ",
      "tick_size": "0.0001",
      "min_limit_order_size": "0.001", 
      "price": "0.991",
      "volume_24h": "16,183.328 INJ",
      "high_24h": "0.9941",
      "low_24h": "0.9901",
      "change_24h": "+0.08%",
      "helix_link": "https://helixapp.com/spot/hinj-inj",
      "timestamp": "2023-04-25T12:34:56.789Z"
    },
    // More coins...
  ]
}
```

## Notes for Integration

When integrating with other systems, you can:
- Use the market_id as a unique identifier for each trading pair
- Follow the helix_link for direct access to each coin's page
- Monitor timestamp values to ensure data freshness 