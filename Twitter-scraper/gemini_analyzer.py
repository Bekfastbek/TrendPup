import json
import pandas as pd
import re
from datetime import datetime
import google.generativeai as genai
import logging
from collections import defaultdict
import time
import backoff
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = ""
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Constants
BATCH_SIZE = 10  # Number of coins to process before saving
RATE_LIMIT_DELAY = 5  # Base delay between API calls in seconds
MAX_RETRIES = 10
CACHE_FILE = 'analyzed_coins_cache.json'

def extract_coin_info(text):
    """Extract potential coin symbols and names from text."""
    # Match $SYMBOL pattern
    dollar_symbols = re.findall(r'\$([A-Z0-9]{2,10})', text)
    
    # Match #SYMBOL pattern
    hash_symbols = re.findall(r'#([A-Z0-9]{2,10})(?=\s|$)', text)
    
    # Extract telegram links
    telegram_links = re.findall(r'https?://t\.me/\S+', text)
    
    # Extract other links
    other_links = re.findall(r'https?://(?!t\.me)\S+', text)
    
    return {
        'symbols': list(set(dollar_symbols + hash_symbols)),
        'telegram_links': telegram_links,
        'other_links': other_links
    }

def load_cache():
    """Load previously analyzed coins from cache."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    return {'analyzed_coins': [], 'processed_symbols': set()}

def save_cache(analyzed_coins, processed_symbols):
    """Save current progress to cache file."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'analyzed_coins': analyzed_coins,
                'processed_symbols': list(processed_symbols)
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"Progress saved to cache file")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

@backoff.on_exception(
    backoff.expo,
    Exception,
    max_tries=MAX_RETRIES,
    max_time=300,
    base=2,
    factor=RATE_LIMIT_DELAY
)
def analyze_coin_with_gemini(coin_data):
    """Use Gemini to analyze coin data and generate insights with improved retry logic."""
    prompt = f"""Analyze this memecoin data and provide a structured assessment.
    Return ONLY valid JSON without any other text.
    
    Data to analyze:
    - Symbol: {list(coin_data['symbols'])[0] if coin_data['symbols'] else 'Unknown'}
    - Number of mentions: {coin_data['mention_count']}
    - Sample tweets: {coin_data['tweet_text'][:2]}
    - Links found: {list(coin_data['links'])}
    - Telegram groups: {list(coin_data['telegram'])}
    
    Format your response as this exact JSON structure:
    {{
        "risk_score": <number 1-10>,
        "potential_score": <number 1-10>,
        "community_score": <number 1-10>,
        "red_flags": ["flag1", "flag2"],
        "positive_indicators": ["indicator1", "indicator2"],
        "recommendation": "brief_recommendation"
    }}"""
    
    try:
        # Add a longer delay between requests
        time.sleep(RATE_LIMIT_DELAY)
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean the response text to ensure it's valid JSON
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        analysis = json.loads(response_text)
        
        # Validate the response structure
        required_fields = ['risk_score', 'potential_score', 'community_score', 
                         'red_flags', 'positive_indicators', 'recommendation']
        for field in required_fields:
            if field not in analysis:
                raise ValueError(f"Missing required field: {field}")
        
        return analysis
    
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return {
            "risk_score": 0,
            "potential_score": 0,
            "community_score": 0,
            "red_flags": ["Analysis failed"],
            "positive_indicators": [],
            "recommendation": "Analysis failed"
        }

def process_tweets(json_file):
    """Process tweet data and extract coin information."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        return None

    # Load cache
    cache_data = load_cache()
    analyzed_coins = cache_data['analyzed_coins']
    processed_symbols = set(cache_data['processed_symbols'])

    coin_data = defaultdict(lambda: {
        'symbols': set(),
        'tweet_text': [],
        'links': set(),
        'telegram': set(),
        'mention_count': 0,
        'first_seen': None,
        'latest_seen': None,
        'categories': set(),
        'search_terms': set()
    })

    # Process each tweet
    for tweet in tweets:
        extracted = extract_coin_info(tweet['text'])
        
        for symbol in extracted['symbols']:
            # Skip if already processed
            if symbol in processed_symbols:
                continue
                
            data = coin_data[symbol]
            data['symbols'].add(symbol)
            data['tweet_text'].append(tweet['text'])
            data['links'].update(extracted['other_links'])
            data['telegram'].update(extracted['telegram_links'])
            data['mention_count'] += 1
            data['categories'].add(tweet['category'])
            data['search_terms'].add(tweet['search_term'])
            
            tweet_time = datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00'))
            if not data['first_seen'] or tweet_time < data['first_seen']:
                data['first_seen'] = tweet_time
            if not data['latest_seen'] or tweet_time > data['latest_seen']:
                data['latest_seen'] = tweet_time

    # Process coins in batches
    coins_to_process = list(coin_data.items())
    total_coins = len(coins_to_process)
    
    for batch_start in range(0, total_coins, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_coins)
        batch = coins_to_process[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_start//BATCH_SIZE + 1}/{(total_coins + BATCH_SIZE - 1)//BATCH_SIZE}")
        
        for idx, (symbol, data) in enumerate(batch, 1):
            logger.info(f"Analyzing coin {batch_start + idx}/{total_coins}: ${symbol}")
            
            try:
                analysis = analyze_coin_with_gemini(data)
                
                analyzed_coin = {
                    'symbol': symbol,
                    'mention_count': data['mention_count'],
                    'first_seen': data['first_seen'].isoformat() if data['first_seen'] else None,
                    'latest_seen': data['latest_seen'].isoformat() if data['latest_seen'] else None,
                    'categories': list(data['categories']),
                    'search_terms': list(data['search_terms']),
                    'telegram_links': list(data['telegram']),
                    'other_links': list(data['links']),
                    'risk_score': analysis['risk_score'],
                    'potential_score': analysis['potential_score'],
                    'community_score': analysis['community_score'],
                    'red_flags': analysis['red_flags'],
                    'positive_indicators': analysis['positive_indicators'],
                    'recommendation': analysis['recommendation'],
                    'sample_tweets': data['tweet_text'][:3]
                }
                
                analyzed_coins.append(analyzed_coin)
                processed_symbols.add(symbol)
                
            except Exception as e:
                logger.error(f"Error processing coin {symbol}: {e}")
        
        # Save progress after each batch
        save_cache(analyzed_coins, processed_symbols)
        
        # Add delay between batches
        if batch_end < total_coins:
            logger.info(f"Waiting {RATE_LIMIT_DELAY * 2} seconds before next batch...")
            time.sleep(RATE_LIMIT_DELAY * 2)

    # Sort by potential score and mention count
    analyzed_coins.sort(key=lambda x: (-x['potential_score'], -x['mention_count']))
    
    # Save final results
    output_file = 'analyzed_memecoins.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis_timestamp': datetime.now().isoformat(),
                'total_coins_analyzed': len(analyzed_coins),
                'coins': analyzed_coins
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"Analysis complete. Results saved to {output_file}")
        
        # Clear cache after successful completion
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            
    except Exception as e:
        logger.error(f"Error saving final results: {e}")
    
    return analyzed_coins

def main():
    logger.info("Starting memecoin analysis...")
    try:
        analyzed_coins = process_tweets('twitter_data.json')
        
        # Print summary of findings
        if analyzed_coins:
            logger.info("\nTop 5 Potential Memecoins:")
            for coin in analyzed_coins[:5]:
                logger.info(f"\nSymbol: ${coin['symbol']}")
                logger.info(f"Potential Score: {coin['potential_score']}/10")
                logger.info(f"Risk Score: {coin['risk_score']}/10")
                logger.info(f"Recommendation: {coin['recommendation']}")
                logger.info("-" * 50)
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main() 