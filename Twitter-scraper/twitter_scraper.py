#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, TimeoutError
import re
import numpy as np
from collections import defaultdict
import time
import google.generativeai as genai
from dotenv import load_dotenv
import random

# Load environment variables from .env file
load_dotenv()

# Get the script's directory for relative file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, "twitter_scraper.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("twitter_scraper")

# Path to Twitter cookies file
COOKIES_FILE = os.path.join(SCRIPT_DIR, "twitter_cookies.json")
# Path to helix data file
HELIX_DATA_FILE = os.path.join(SCRIPT_DIR, "helix_data.json")
# Path to output Twitter data file
TWITTER_DATA_FILE = os.path.join(SCRIPT_DIR, "twitter_coin_data.json")
# Path to analysis output file
ANALYSIS_OUTPUT_FILE = os.path.join(SCRIPT_DIR, "coin_investment_analysis.json")

# Get Gemini API keys from environment variables
GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]

# Filter out None or empty API keys
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]

if not GEMINI_API_KEYS:
    logger.error("No valid Gemini API keys found in environment variables")
    sys.exit(1)

logger.info(f"Found {len(GEMINI_API_KEYS)} Gemini API keys")

def load_helix_data():
    """Load coin data from helix_data.json"""
    try:
        with open(HELIX_DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading helix data: {e}")
        return None

def extract_coin_symbols(helix_data):
    """Extract coin symbols from helix data"""
    coins = []
    if not helix_data or 'data' not in helix_data:
        return coins
    
    for item in helix_data['data']:
        if 'symbol' in item:
            # Extract the coin part before /INJ
            symbol = item['symbol'].split('/')[0]
            coins.append(symbol)
    
    logger.info(f"Extracted {len(coins)} coin symbols from helix data")
    return coins

def normalize_cookies(cookies):
    """
    Normalize cookie format for Playwright
    Specifically fixes the sameSite attribute to be one of: "Strict", "Lax", or "None"
    """
    normalized_cookies = []
    
    for cookie in cookies:
        # Create a copy of the cookie to modify
        normalized_cookie = cookie.copy()
        
        # Fix sameSite attribute if it exists
        if 'sameSite' in normalized_cookie:
            same_site = normalized_cookie['sameSite']
            # Handle None values
            if same_site is None:
                normalized_cookie['sameSite'] = 'Lax'  # Use Lax as default
            else:
                # Map common values to the correct formats
                same_site_lower = str(same_site).lower()
                if same_site_lower in ['no_restriction', 'none']:
                    normalized_cookie['sameSite'] = 'None'
                elif same_site_lower in ['lax']:
                    normalized_cookie['sameSite'] = 'Lax'
                elif same_site_lower in ['strict']:
                    normalized_cookie['sameSite'] = 'Strict'
                else:
                    # Default to Lax if unknown
                    normalized_cookie['sameSite'] = 'Lax'
        
        # Some cookies from browsers may have these fields that Playwright doesn't accept
        for field in ['hostOnly', 'session', 'storeId']:
            if field in normalized_cookie:
                del normalized_cookie[field]
                
        # Add the normalized cookie
        normalized_cookies.append(normalized_cookie)
    
    return normalized_cookies

async def load_cookies(context):
    """Load cookies from the cookies file"""
    try:
        with open(COOKIES_FILE, 'r') as f:
            original_cookies = json.load(f)
        
        # Normalize cookies to match Playwright's expected format
        normalized_cookies = normalize_cookies(original_cookies)
        
        logger.info(f"Normalizing {len(original_cookies)} cookies for Playwright compatibility")
        
        # Add normalized cookies to the browser context
        await context.add_cookies(normalized_cookies)
        logger.info(f"Successfully loaded {len(normalized_cookies)} cookies")
        return True
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        logger.error("You may need to refresh your Twitter cookies or provide them in the correct format")
        return False

async def search_twitter_for_coin(page, coin_symbol):
    """Search Twitter for a specific coin symbol"""
    search_url = f"https://twitter.com/search?q=%24{coin_symbol}%20OR%20{coin_symbol}%20crypto&src=typed_query&f=live"
    
    try:
        logger.info(f"Searching Twitter for {coin_symbol}")
        
        # Navigate to search URL with extended timeout
        await page.goto(search_url, timeout=120000)  # Increase timeout to 2 minutes
        
        # Wait for DOM content loaded instead of networkidle (less strict)
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
        except Exception as e:
            logger.warning(f"Page load state timeout for {coin_symbol}, continuing anyway: {e}")
        
        # Sleep a moment to allow page to stabilize
        await asyncio.sleep(3)
        
        # Wait for tweets to load with more resilient approach
        try:
            # Try to find any tweet elements
            tweet_selector = 'article[data-testid="tweet"]'
            has_tweets = await page.query_selector(tweet_selector) is not None
            
            # If initial check doesn't find tweets, wait for them to appear
            if not has_tweets:
                logger.info(f"Waiting for tweets to load for {coin_symbol}...")
                await page.wait_for_selector(tweet_selector, timeout=20000)
        except Exception as e:
            logger.warning(f"No tweets found for {coin_symbol}: {e}")
            return []
        
        # Scroll to load more tweets with error handling
        for i in range(3):
            try:
                await page.evaluate('window.scrollBy(0, 1000)')
                await asyncio.sleep(2)  # Give more time for content to load
            except Exception as e:
                logger.warning(f"Error scrolling for {coin_symbol} (scroll #{i+1}): {e}")
                # Continue despite scroll errors
        
        # Extract tweets with improved error handling
        try:
            tweets = await page.evaluate("""
            () => {
                const tweets = [];
                const tweetElements = document.querySelectorAll('article[data-testid="tweet"]');
                
                if (!tweetElements || tweetElements.length === 0) {
                    return tweets; // Return empty array if no tweets
                }
                
                tweetElements.forEach(tweet => {
                    try {
                        // Username and handle
                        const userElement = tweet.querySelector('div[data-testid="User-Name"]');
                        const username = userElement ? userElement.querySelector('span:first-child')?.textContent : null;
                        const handleElement = userElement ? userElement.querySelector('span:nth-child(2)')?.textContent : null;
                        
                        // Tweet text
                        const textElement = tweet.querySelector('div[data-testid="tweetText"]');
                        const text = textElement ? textElement.textContent : null;
                        
                        // Time
                        const timeElement = tweet.querySelector('time');
                        const timestamp = timeElement ? timeElement.getAttribute('datetime') : null;
                        
                        // Engagement metrics
                        const replyElement = tweet.querySelector('div[data-testid="reply"]');
                        const replyCount = replyElement ? replyElement.textContent : '0';
                        
                        const retweetElement = tweet.querySelector('div[data-testid="retweet"]');
                        const retweetCount = retweetElement ? retweetElement.textContent : '0';
                        
                        const likeElement = tweet.querySelector('div[data-testid="like"]');
                        const likeCount = likeElement ? likeElement.textContent : '0';
                        
                        // URL
                        const linkElement = tweet.querySelector('a[href*="/status/"]');
                        const url = linkElement ? 'https://twitter.com' + linkElement.getAttribute('href') : null;
                        
                        // Only add tweet if we have at least text or username
                        if (text || username) {
                            tweets.push({
                                username: username || "Unknown",
                                handle: handleElement || "",
                                text: text || "(No text)",
                                timestamp: timestamp || "",
                                reply_count: parseEngagementCount(replyCount),
                                retweet_count: parseEngagementCount(retweetCount),
                                like_count: parseEngagementCount(likeCount),
                                url: url || ""
                            });
                        }
                    } catch (error) {
                        console.error('Error parsing tweet:', error);
                    }
                });
                
                function parseEngagementCount(countText) {
                    if (!countText) return 0;
                    countText = countText.trim();
                    if (countText === '') return 0;
                    
                    try {
                        if (countText.includes('K')) {
                            return parseInt(parseFloat(countText.replace('K', '')) * 1000);
                        } else if (countText.includes('M')) {
                            return parseInt(parseFloat(countText.replace('M', '')) * 1000000);
                        } else {
                            return parseInt(countText);
                        }
                    } catch (e) {
                        return 0;
                    }
                }
                
                return tweets;
            }
            """)
        except Exception as e:
            logger.error(f"Error extracting tweets for {coin_symbol}: {e}")
            return []
        
        # Add metadata to tweets
        for tweet in tweets:
            tweet['coin_symbol'] = coin_symbol
            tweet['discovery_time'] = datetime.now().isoformat()
        
        logger.info(f"Found {len(tweets)} tweets for {coin_symbol}")
        return tweets
    
    except Exception as e:
        logger.error(f"Error searching Twitter for {coin_symbol}: {e}")
        return []

def analyze_sentiment_with_gemini(tweets_text, coin_symbol):
    """
    Analyze tweet sentiment using Google's Gemini API
    Returns a dict with sentiment score and investment analysis
    """
    if not tweets_text:
        logger.warning(f"No tweets to analyze for {coin_symbol}")
        return {"sentiment_score": 0, "analysis": "No data available"}
    
    # Rotate through available API keys to avoid rate limits
    api_key = random.choice(GEMINI_API_KEYS)
    genai.configure(api_key=api_key)
    
    try:
        # Configure the model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create the prompt for Gemini
        prompt = f"""
        Analyze the following tweets about the cryptocurrency {coin_symbol} for investment sentiment.
        
        Tweets:
        {tweets_text}
        
        Please provide:
        1. A sentiment score from -1.0 (extremely negative) to 1.0 (extremely positive)
        2. A brief analysis of why this cryptocurrency might be a good or bad investment based on these tweets
        3. Key factors mentioned in the tweets that could affect the price
        
        Format your response as JSON only, with the following structure:
        {{
            "sentiment_score": [score as a float],
            "investment_analysis": "[brief analysis]",
            "key_factors": ["factor1", "factor2", ...]
        }}
        """
        
        # Generate the response
        response = model.generate_content(prompt)
        
        # Parse the response as JSON
        response_text = response.text
        # Extract JSON if surrounded by markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Gemini response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            
            # Fallback to simple sentiment extraction
            if isinstance(response_text, str) and "sentiment_score" in response_text:
                try:
                    # Try to extract just the sentiment score with regex
                    match = re.search(r'"sentiment_score"\s*:\s*([-+]?\d*\.\d+|\d+)', response_text)
                    if match:
                        sentiment_score = float(match.group(1))
                        return {"sentiment_score": sentiment_score, "analysis": "Partial analysis only"}
                except Exception:
                    pass
                    
            return {"sentiment_score": 0, "analysis": "Failed to parse analysis"}
    
    except Exception as e:
        logger.error(f"Error calling Gemini API for {coin_symbol}: {e}")
        return {"sentiment_score": 0, "analysis": f"API error: {str(e)}"}

def analyze_coin_data(helix_data, twitter_data):
    """Analyze coin data from helix and Twitter to find top investment opportunities"""
    coin_analysis = {}
    helix_coins_map = {}
    
    # Create a map of coin symbols to helix data
    for item in helix_data['data']:
        symbol = item['symbol'].split('/')[0]
        price_str = item['price']
        
        # Handle price formatting issues
        try:
            # Remove commas and any other non-numeric characters except decimal points
            clean_price = re.sub(r'[^\d.]', '', price_str)
            price = float(clean_price) if clean_price else 0.0
        except (ValueError, TypeError):
            price = 0.0
        
        change_str = item['change_24h']
        try:
            change = float(change_str.strip('%')) if change_str != 'N/A' else 0.0
        except (ValueError, TypeError):
            change = 0.0
        
        helix_coins_map[symbol] = {
            'price': price,
            'change_24h': change
        }
    
    # Group tweets by coin
    coin_tweets = defaultdict(list)
    for tweet in twitter_data:
        coin_tweets[tweet['coin_symbol']].append(tweet)
    
    # Analyze each coin
    for coin, tweets in coin_tweets.items():
        if coin not in helix_coins_map:
            continue
        
        # Calculate engagement metrics
        total_likes = sum(tweet['like_count'] for tweet in tweets)
        total_retweets = sum(tweet['retweet_count'] for tweet in tweets)
        total_replies = sum(tweet['reply_count'] for tweet in tweets)
        tweet_count = len(tweets)
        
        # Aggregate tweet texts for Gemini analysis
        all_tweet_texts = "\n".join([f"{i+1}. {tweet.get('text', '')}" for i, tweet in enumerate(tweets[:10])])
        
        # Get Gemini analysis
        gemini_result = analyze_sentiment_with_gemini(all_tweet_texts, coin)
        sentiment_score = gemini_result.get('sentiment_score', 0)
        investment_analysis = gemini_result.get('investment_analysis', '')
        key_factors = gemini_result.get('key_factors', [])
        
        # Price data
        price = helix_coins_map[coin]['price']
        price_change = helix_coins_map[coin]['change_24h']
        
        # Calculate a score based on engagement, sentiment and price change
        engagement_score = (total_likes + total_retweets*2 + total_replies*1.5) / max(1, tweet_count)
        
        # Only consider coins with valid prices
        if price > 0:
            # Calculate investment score with heavier weight on Gemini sentiment analysis
            investment_score = (
                (engagement_score * 0.3) + 
                (sentiment_score * 40) + 
                (price_change * 0.5)
            )
            
            coin_analysis[coin] = {
                'symbol': coin,
                'price': price,
                'price_change_24h': price_change,
                'tweet_count': tweet_count,
                'total_likes': total_likes,
                'total_retweets': total_retweets,
                'total_replies': total_replies,
                'engagement_score': engagement_score,
                'sentiment_score': sentiment_score,
                'gemini_analysis': investment_analysis,
                'key_factors': key_factors,
                'investment_score': investment_score
            }
    
    # Sort coins by investment score
    sorted_coins = sorted(
        coin_analysis.values(), 
        key=lambda x: x['investment_score'], 
        reverse=True
    )
    
    # Get top 10 or all if less than 10
    top_coins = sorted_coins[:min(10, len(sorted_coins))]
    
    return top_coins

async def scrape_twitter_for_coins():
    """Main function to scrape Twitter for coin data"""
    # Load helix data
    helix_data = load_helix_data()
    if not helix_data:
        logger.error("Failed to load helix data, exiting")
        return False
    
    # Extract coin symbols
    coin_symbols = extract_coin_symbols(helix_data)
    if not coin_symbols:
        logger.error("No coin symbols found in helix data, exiting")
        return False
    
    all_tweets = []
    
    async with async_playwright() as p:
        # Launch browser options - configured for virtual X server
        browser_launch_options = {
            "headless": False,  # Use "headed" mode with virtual X server
            "timeout": 120000,  # Increase timeout to 2 minutes
            "args": [
                "--disable-web-security",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",  # Disable GPU acceleration
                "--mute-audio",   # Mute audio to avoid issues
                "--window-size=1280,800"  # Set window size
            ]
        }
        
        logger.info("Launching browser in headed mode with virtual X server")
        browser = await p.chromium.launch(**browser_launch_options)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
        )
        
        # Take screenshots for debugging
        screenshot_dir = os.path.join(SCRIPT_DIR, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Load cookies
        cookies_loaded = await load_cookies(context)
        if not cookies_loaded:
            logger.error("Failed to load cookies, exiting")
            await browser.close()
            return False
        
        # Create a new page
        page = await context.new_page()
        
        try:
            # First visit Twitter search page directly instead of homepage
            # This is less likely to trigger login requirements or timeouts
            general_search_url = "https://twitter.com/search?q=crypto&src=typed_query&f=live"
            logger.info("Visiting Twitter search page to initialize session")
            
            try:
                await page.goto(general_search_url, timeout=120000)  # Increase timeout to 2 minutes
                
                # Use a more lenient approach to wait for page load
                try:
                    await page.wait_for_load_state('domcontentloaded', timeout=30000)
                    logger.info("Twitter search page DOM loaded")
                except TimeoutError:
                    logger.warning("Timeout waiting for page load state, continuing anyway")
                
                # Wait for some content to appear
                await asyncio.sleep(5)  # Give the page a moment to initialize
                
                # Take a screenshot after initial page load
                await page.screenshot(path=os.path.join(screenshot_dir, "twitter_initial.png"))
                logger.info(f"Saved initial screenshot")
            except Exception as e:
                logger.warning(f"Issue with initial page load: {e}")
                logger.info("Will attempt to continue with searches anyway")
            
            # Scrape data for each coin
            processed_count = 0
            for coin in coin_symbols:
                if not coin:
                    continue
                
                try:
                    tweets = await search_twitter_for_coin(page, coin)
                    
                    # Only take screenshots for some coins to avoid disk space issues
                    if processed_count % 5 == 0:  # Take screenshot every 5 coins
                        try:
                            await page.screenshot(path=os.path.join(screenshot_dir, f"search_{coin}.png"))
                        except Exception as e:
                            logger.warning(f"Failed to take screenshot for {coin}: {e}")
                    
                    all_tweets.extend(tweets)
                    processed_count += 1
                    
                    # Log progress periodically
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(coin_symbols)} coins, found {len(all_tweets)} tweets so far")
                except Exception as e:
                    logger.error(f"Error processing coin {coin}: {e}")
                    # Continue with next coin
                
                # Add a short delay between requests to avoid rate limiting
                await asyncio.sleep(3)  # Increase delay between requests
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            try:
                # Ensure browser is closed properly
                await browser.close()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    # Save all tweets to file
    with open(TWITTER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_tweets, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(all_tweets)} tweets to {TWITTER_DATA_FILE}")
    
    # Analyze the data if we have tweets
    if all_tweets:
        logger.info("Starting coin analysis with Gemini API")
        top_coins = analyze_coin_data(helix_data, all_tweets)
        
        # Save analysis results
        analysis_result = {
            "top_investment_coins": top_coins,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_coins_analyzed": len(coin_symbols),
            "total_tweets_analyzed": len(all_tweets)
        }
        
        with open(ANALYSIS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Analysis complete. Top {len(top_coins)} coins saved to {ANALYSIS_OUTPUT_FILE}")
        
        # Print top coins to console
        print("\n===== TOP COINS TO INVEST IN =====")
        for i, coin in enumerate(top_coins, 1):
            print(f"{i}. {coin['symbol']} - Price: ${coin['price']:.6f} - Change: {coin['price_change_24h']}%")
            print(f"   Score: {coin['investment_score']:.2f} | Sentiment: {coin['sentiment_score']:.2f}")
            print(f"   Analysis: {coin['gemini_analysis']}")
            print(f"   Key factors: {', '.join(coin['key_factors']) if coin['key_factors'] else 'None identified'}")
            print()
        print("=================================\n")
    
    return True

async def main():
    """Main entry point"""
    logger.info("Starting Twitter coin scraper and analyzer with Gemini AI")
    await scrape_twitter_for_coins()

if __name__ == "__main__":
    asyncio.run(main()) 