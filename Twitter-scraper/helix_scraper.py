import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError

# Get the script's directory for relative file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, "helix_scraper.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("helix_scraper")

# URL to scrape
HELIX_URL = "https://helixapp.com/spot/inj-usdt"

async def scrape_helix_inj_pairs():
    """
    Scrape cryptocurrency data from Helix App for pairs ending with /INJ
    """
    logger.info("Starting Helix scraper for /INJ pairs")
    
    async with async_playwright() as p:
        # Launch options with increased timeouts and more browser settings
        browser_launch_options = {
            "headless": False,
            "timeout": 60000,  # 60 seconds for browser launch
            "args": [
                "--disable-web-security",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        }
        
        logger.info("Launching browser with options: %s", browser_launch_options)
        browser = await p.chromium.launch(**browser_launch_options)
        
        # Create context with a larger viewport and longer timeout
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Set default timeout for all operations to 60 seconds
        context.set_default_timeout(60000)
        
        page = await context.new_page()
        
        try:
            # Navigate to the Helix App with a longer timeout
            logger.info(f"Navigating to {HELIX_URL}")
            await page.goto(HELIX_URL, timeout=60000, wait_until="domcontentloaded")
            
            # Wait for page to load with a longer timeout and more specific approach
            logger.info("Waiting for page to load...")
            
            try:
                # Try waiting for specific elements first that would indicate the page is loaded
                await page.wait_for_selector("body", timeout=10000)
                logger.info("Body element found, waiting for more content...")
                
                # Try with a more flexible approach
                try:
                    await page.wait_for_load_state("networkidle", timeout=60000)
                    logger.info("Network idle state reached")
                except TimeoutError:
                    logger.warning("Network idle timeout reached, continuing anyway as page might still be usable")
            except TimeoutError as e:
                logger.warning(f"Timeout while waiting for page elements: {e}")
                logger.info("Continuing anyway as page might still be partially loaded")
            
            # Give extra time for dynamic content to load
            logger.info("Waiting additional time for dynamic content to load...")
            await asyncio.sleep(10)
            
            # Click on the "All Markets" dropdown button
            logger.info("Looking for 'All Markets' dropdown button...")
            
            # Try multiple selectors that might match the "All Markets" dropdown
            all_markets_selectors = [
                "text=All Markets",
                "[aria-label='All Markets']",
                "button:has-text('All Markets')",
                "div:has-text('All Markets'):not(:has(*))",
                "//button[contains(., 'All Markets')]",
                "//div[contains(., 'All Markets') and not(child::*)]"
            ]
            
            clicked = False
            for selector in all_markets_selectors:
                try:
                    logger.info(f"Trying to click using selector: {selector}")
                    # Wait for the element to be visible and clickable
                    await page.wait_for_selector(selector, state="visible", timeout=5000)
                    await page.click(selector)
                    logger.info(f"Successfully clicked 'All Markets' using selector: {selector}")
                    clicked = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to click with selector '{selector}': {e}")
            
            if not clicked:
                logger.warning("Could not click on 'All Markets' dropdown using predefined selectors")
                logger.info("Trying to find and click based on visual content...")
                
                # Try to find and click the element by analyzing the page content
                dropdown_element = await page.evaluate('''
                () => {
                    // Find elements containing "All Markets" text
                    const elements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent.trim() === 'All Markets');
                    
                    if (elements.length > 0) {
                        // Get coordinates for click
                        const rect = elements[0].getBoundingClientRect();
                        return {
                            x: rect.x + rect.width / 2,
                            y: rect.y + rect.height / 2,
                            found: true
                        };
                    }
                    return { found: false };
                }
                ''')
                
                if dropdown_element and dropdown_element.get('found'):
                    logger.info(f"Found 'All Markets' element via content analysis, clicking at coordinates: {dropdown_element.get('x')}, {dropdown_element.get('y')}")
                    await page.mouse.click(dropdown_element.get('x'), dropdown_element.get('y'))
                    clicked = True
                else:
                    logger.warning("Could not find 'All Markets' element via content analysis")
            
            # Wait for dropdown to appear and search for "/INJ"
            if clicked:
                logger.info("Waiting for dropdown to appear...")
                await asyncio.sleep(2)
                
                # Look for a search input in the dropdown
                search_selectors = [
                    "input[placeholder*='Search']",
                    "input[type='text']",
                    "input",
                    "[role='searchbox']",
                    "[aria-label='Search']"
                ]
                
                search_input_found = False
                for selector in search_selectors:
                    try:
                        logger.info(f"Looking for search input with selector: {selector}")
                        search_input = await page.wait_for_selector(selector, state="visible", timeout=5000)
                        if search_input:
                            logger.info(f"Found search input using selector: {selector}")
                            # Type "/INJ" in the search input
                            await search_input.fill("/INJ")
                            logger.info("Entered '/INJ' in search input")
                            await asyncio.sleep(2)  # Wait for search results
                            search_input_found = True
                            break
                    except Exception as e:
                        logger.warning(f"Failed to find or fill search input with selector '{selector}': {e}")
                
                if not search_input_found:
                    logger.warning("Could not find search input in dropdown")
            
            # Wait for search results
            logger.info("Waiting for search results to load...")
            await asyncio.sleep(3)
            
            # Extract cryptocurrency data
            logger.info("Extracting cryptocurrency data from search results...")
            
            cryptos = await page.evaluate('''
            () => {
                // This function runs in the browser context
                const cryptoData = [];
                console.log("Browser context: Starting data extraction after search");
                
                // Function to process trading pair elements
                function processPairElements(elements) {
                    elements.forEach(el => {
                        const text = el.textContent || '';
                        
                        // Look for patterns like XXX/INJ or XXX/inj (case insensitive)
                        const symbolMatch = text.match(/([A-Z0-9]+)\/INJ/i);
                        if (symbolMatch) {
                            const symbol = symbolMatch[0].toUpperCase(); // Ensure proper casing
                            console.log("Browser context: Found trading pair:", symbol);
                            
                            // Extract price, volume, and change data from the element's structure
                            // This assumes the data is in the element or its children
                            let price = 'N/A';
                            let volume = 'N/A';
                            let change_24h = 'N/A';
                            
                            // Look for price (typically a number with optional $ symbol)
                            const priceMatch = text.match(/[$]?([0-9,.]+)/);
                            if (priceMatch) {
                                price = priceMatch[0];
                            }
                            
                            // Look for volume (typically a number followed by K, M, B)
                            const volumeMatch = text.match(/[$]?([0-9,.]+[KMB]?)/i);
                            if (volumeMatch && volumeMatch[0] !== price) {
                                volume = volumeMatch[0];
                            }
                            
                            // Look for 24h change (typically a percentage with + or - sign)
                            const changeMatch = text.match(/([+-][0-9,.]+%)/);
                            if (changeMatch) {
                                change_24h = changeMatch[0];
                            }
                            
                            // Add to our results
                            cryptoData.push({
                                symbol: symbol,
                                price: price,
                                volume: volume,
                                change_24h: change_24h,
                                timestamp: new Date().toISOString()
                            });
                        }
                    });
                }
                
                // Scenario 1: Look for trading pairs in a dropdown or popover
                const dropdownElements = document.querySelectorAll('.dropdown-content li, .popover-content li, [role="listitem"]');
                console.log("Browser context: Found dropdown/popover elements:", dropdownElements.length);
                processPairElements(dropdownElements);
                
                // Scenario 2: Look for trading pairs in a table or list
                const tableElements = document.querySelectorAll('tr, li, div[class*="row"], div[class*="item"]');
                console.log("Browser context: Found table/list elements:", tableElements.length);
                processPairElements(tableElements);
                
                // Scenario 3: General approach - look for any elements that might contain trading pairs
                if (cryptoData.length === 0) {
                    console.log("Browser context: No trading pairs found in specific elements, trying general approach");
                    const allElements = document.querySelectorAll('*');
                    const potentialElements = Array.from(allElements).filter(el => {
                        const text = el.textContent || '';
                        return text.includes('/INJ') && !text.includes('>') && !text.includes('<') && el.children.length === 0;
                    });
                    
                    console.log("Browser context: Found potential elements with /INJ:", potentialElements.length);
                    processPairElements(potentialElements);
                }
                
                console.log("Browser context: Total trading pairs found:", cryptoData.length);
                return cryptoData;
            }
            ''')
            
            logger.info(f"Extracted {len(cryptos) if cryptos else 0} cryptocurrency pairs from page")
            
            # If we didn't find data with the initial extraction, try an alternative approach
            if not cryptos:
                logger.info("Initial extraction didn't yield results, trying alternative approach")
                
                # Save the HTML for analysis
                html_content = await page.content()
                html_path = os.path.join(SCRIPT_DIR, "helix_page.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Page HTML saved to {html_path}")
                
                # Try to extract using regex pattern matching on the HTML
                logger.info("Trying regex pattern matching on HTML content")
                
                def extract_inj_pairs(html):
                    import re
                    # Pattern to find cryptocurrency pairs ending with /INJ
                    pattern = r'([A-Z0-9]+)/INJ'
                    matches = re.findall(pattern, html)
                    
                    results = []
                    seen = set()
                    for match in matches:
                        pair = f"{match}/INJ"
                        if pair not in seen:
                            seen.add(pair)
                            logger.info(f"Found trading pair via regex: {pair}")
                            results.append({
                                "symbol": pair,
                                "price": "N/A",
                                "volume": "N/A",
                                "change_24h": "N/A",
                                "timestamp": datetime.now().isoformat()
                            })
                    return results
                
                cryptos = extract_inj_pairs(html_content)
                logger.info(f"Regex extraction found {len(cryptos)} trading pairs")
            
            # Filter data to ensure we only have /INJ pairs and remove duplicates
            inj_cryptos = []
            seen_symbols = set()
            
            for crypto in (cryptos or []):
                symbol = crypto.get('symbol', '')
                if symbol and symbol.endswith('/INJ') and symbol not in seen_symbols:
                    seen_symbols.add(symbol)
                    inj_cryptos.append(crypto)
            
            logger.info(f"Found {len(inj_cryptos)} unique cryptocurrency pairs ending with /INJ")
            
            # Add timestamp and source information
            result = {
                "data": inj_cryptos,
                "metadata": {
                    "source": HELIX_URL,
                    "timestamp": datetime.now().isoformat(),
                    "count": len(inj_cryptos)
                }
            }
            
            # Save the data to a JSON file
            json_path = os.path.join(SCRIPT_DIR, "helix_data.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Data saved to {json_path}")
            await browser.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            await browser.close()
            raise

async def main():
    try:
        result = await scrape_helix_inj_pairs()
        logger.info(f"Successfully scraped {len(result['data'])} INJ pairs")
    except Exception as e:
        logger.error(f"Error in Helix scraper: {e}", exc_info=True)
        return 1
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 