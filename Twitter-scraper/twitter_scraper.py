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

async def load_cookies(context):
    """Load cookies from the cookies file"""
    try:
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        logger.info(f"Loaded {len(cookies)} cookies from {COOKIES_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return False

async def search_twitter_for_coin(page, coin_symbol):
    """Search Twitter for a specific coin symbol"""
    search_url = f"https://twitter.com/search?q=%24{coin_symbol}%20OR%20{coin_symbol}%20crypto&src=typed_query&f=live"
    
    try:
        logger.info(f"Searching Twitter for {coin_symbol}")
        await page.goto(search_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Wait for tweets to load
        try:
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
        except TimeoutError:
            logger.warning(f"No tweets found for {coin_symbol}")
            return []
        
        # Scroll to load more tweets
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(1)
        
        # Extract tweets
        tweets = await page.evaluate("""
        () => {
            const tweets = [];
            const tweetElements = document.querySelectorAll('article[data-testid="tweet"]');
            
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
                    
                    tweets.push({
                        username,
                        handle: handleElement,
                        text,
                        timestamp,
                        reply_count: parseEngagementCount(replyCount),
                        retweet_count: parseEngagementCount(retweetCount),
                        like_count: parseEngagementCount(likeCount),
                        url
                    });
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
        model = genai.GenerativeModel('gemini-pro')
        
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
        # Launch browser options - now in headless mode
        browser_launch_options = {
            "headless": True,  # Changed to headless mode
            "timeout": 60000,
            "args": [
                "--disable-web-security",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        }
        
        logger.info("Launching browser in headless mode")
        browser = await p.chromium.launch(**browser_launch_options)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
        )
        
        # Load cookies
        cookies_loaded = await load_cookies(context)
        if not cookies_loaded:
            logger.error("Failed to load cookies, exiting")
            await browser.close()
            return False
        
        # Create a new page
        page = await context.new_page()
        
        # First visit Twitter homepage to ensure cookies are loaded correctly
        logger.info("Visiting Twitter homepage to initialize session")
        await page.goto("https://twitter.com/home", timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Scrape data for each coin
        for coin in coin_symbols:
            if not coin:
                continue
            
            tweets = await search_twitter_for_coin(page, coin)
            all_tweets.extend(tweets)
            
            # Add a short delay between requests to avoid rate limiting
            await asyncio.sleep(2)
        
        await browser.close()
    
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