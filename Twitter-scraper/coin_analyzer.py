import json
import re
import os
import logging
import requests
import time
from datetime import datetime
from collections import Counter, defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai  # Google Generative AI library

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coin_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API endpoints
COINBASE_API_BASE = "https://api.coinbase.com/v2"
COINBASE_PRO_API_BASE = "https://api.exchange.coinbase.com"

# Get Google Gemini AI API keys from environment variables
GEMINI_API_KEYS = [
    os.environ.get("GEMINI_API_KEY", ""),
    os.environ.get("GEMINI_API_KEY_2", ""),
    os.environ.get("GEMINI_API_KEY_3", "")
]

# Gemini model configuration
GEMINI_MODEL = "gemini-2.0-flash"  # Specify the model version to use

class CoinAnalyzer:
    def __init__(self, data_file="twitter_data.json", output_dir="analysis_results"):
        self.data_file = data_file
        self.output_dir = output_dir
        self.tweets = []
        self.coins = defaultdict(dict)
        self.coin_mentions = Counter()
        self.sentiment_scores = defaultdict(list)
        self.current_gemini_api_index = 0
        self.gemini_api_errors = [0, 0, 0]  # Track errors for each API
        self.api_rotation_threshold = 3  # Number of errors before rotating APIs
        
        # Check if we have valid Gemini API keys and initialize Gemini if available
        self.has_gemini_auth = any(GEMINI_API_KEYS)
        if self.has_gemini_auth:
            self._initialize_gemini()
        else:
            logger.warning("No Gemini API keys found in environment variables. AI analysis will be unavailable.")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _initialize_gemini(self):
        """Initialize the Gemini API with current API key"""
        try:
            api_key = self.get_next_gemini_api_key()
            genai.configure(api_key=api_key)
            # Set up the model with appropriate configurations
            self.gemini_config = {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 50,
                "max_output_tokens": 1024,
            }
            
            # Generate model instance - test connection
            model = genai.GenerativeModel(GEMINI_MODEL, generation_config=self.gemini_config)
            logger.info(f"Successfully initialized Gemini model: {GEMINI_MODEL}")
            self.gemini_model = model
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.gemini_api_errors[self.current_gemini_api_index] += 1
            return False

    def load_data(self):
        """Load the tweet data from JSON file"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.tweets = json.load(f)
            logger.info(f"Loaded {len(self.tweets)} tweets from {self.data_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading tweet data: {e}")
            return False

    def extract_coin_symbols(self):
        """Extract coin symbols from tweets"""
        # Common crypto symbol pattern
        symbol_pattern = r'\b[A-Z]{2,10}/(?:INJ|USDT|USD|BTC|ETH)\b|\b[A-Z]{2,10}\b'
        
        for tweet in self.tweets:
            text = tweet.get('text', '')
            # Extract potential coin symbols
            matches = re.findall(symbol_pattern, text)
            for match in matches:
                # Clean and normalize symbol
                symbol = match.split('/')[0] if '/' in match else match
                if symbol not in ["RT", "USD", "USDT", "BTC", "ETH", "INJ"]:  # Filter common non-coin text
                    self.coin_mentions[symbol] += 1
        
        logger.info(f"Extracted {len(self.coin_mentions)} potential coin symbols")
        return self.coin_mentions

    def get_next_gemini_api_key(self):
        """Rotate to the next Gemini API key if the current one has too many errors"""
        if self.gemini_api_errors[self.current_gemini_api_index] >= self.api_rotation_threshold:
            # Reset error count and move to next API
            self.gemini_api_errors[self.current_gemini_api_index] = 0
            self.current_gemini_api_index = (self.current_gemini_api_index + 1) % len(GEMINI_API_KEYS)
            logger.info(f"Rotating to Gemini API key {self.current_gemini_api_index + 1}")
            
            # Reinitialize Gemini with new API key if we've rotated
            if hasattr(self, 'gemini_model'):
                self._initialize_gemini()
        
        return GEMINI_API_KEYS[self.current_gemini_api_index]

    def fetch_coin_details(self, top_n=50):
        """Fetch details for the most mentioned coins from APIs"""
        top_coins = [coin for coin, count in self.coin_mentions.most_common(top_n)]
        logger.info(f"Fetching details for top {len(top_coins)} coins")
        
        futures = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            for coin in top_coins:
                futures.append(
                    executor.submit(self._get_coin_details, coin)
                )
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        symbol, data = result
                        self.coins[symbol] = data
                except Exception as e:
                    logger.error(f"Error fetching coin details: {e}")
        
        logger.info(f"Successfully fetched details for {len(self.coins)} coins")
        return self.coins

    def _get_coin_details(self, symbol):
        """Get details for a specific coin from available APIs"""
        # We'll use Coinbase API for coin details as it doesn't need auth
        return self._get_coinbase_coin_details(symbol)

    def _get_coinbase_coin_details(self, symbol):
        """Get coin details from Coinbase API (no auth needed)"""
        try:
            # Try to get currency info
            response = requests.get(f"{COINBASE_API_BASE}/currencies/{symbol}", timeout=10)
            if response.status_code == 200:
                currency_data = response.json().get('data', {})
                coin_data = {
                    'name': currency_data.get('name', 'Unknown'),
                    'symbol': symbol,
                    'mentions': self.coin_mentions[symbol],
                    'metadata': currency_data,
                    'source': 'coinbase'
                }
                
                # Try to get price info (may not be available for all coins)
                try:
                    price_response = requests.get(f"{COINBASE_API_BASE}/prices/{symbol}-USD/spot", timeout=10)
                    if price_response.status_code == 200:
                        price_data = price_response.json().get('data', {})
                        coin_data['price_usd'] = price_data.get('amount')
                except Exception as e:
                    logger.warning(f"Could not fetch Coinbase price for {symbol}: {e}")
                
                # Add timestamp
                coin_data['analysis_time'] = datetime.now().isoformat()
                
                logger.info(f"Successfully retrieved {symbol} details from Coinbase")
                return symbol, coin_data
            else:
                logger.warning(f"Coin {symbol} not found on Coinbase (Status: {response.status_code})")
                
                # Create minimal data entry if not found
                minimal_data = {
                    'name': symbol,
                    'symbol': symbol,
                    'mentions': self.coin_mentions[symbol],
                    'source': 'minimal',
                    'analysis_time': datetime.now().isoformat()
                }
                return symbol, minimal_data
                
        except Exception as e:
            logger.error(f"Error fetching details from Coinbase for {symbol}: {e}")
            
            # Create minimal data entry for error case
            minimal_data = {
                'name': symbol,
                'symbol': symbol,
                'mentions': self.coin_mentions[symbol],
                'source': 'minimal',
                'analysis_time': datetime.now().isoformat()
            }
            return symbol, minimal_data
    
    def analyze_with_gemini(self, coin, tweets):
        """Use Gemini AI to analyze tweets about a coin"""
        if not self.has_gemini_auth or not hasattr(self, 'gemini_model'):
            logger.warning("Gemini AI not available for analysis")
            return {}
        
        try:
            # Prepare the tweets for analysis
            tweet_texts = [f"Tweet: {tweet.get('text', '')}" for tweet in tweets[:10]]  # Limit to 10 tweets
            
            if not tweet_texts:
                return {}
            
            # Create the prompt - using a join outside the f-string to avoid backslash in expression
            tweets_joined = "\n".join(tweet_texts)
            prompt = f"""
            Analyze these tweets about cryptocurrency {coin}:
            
            {tweets_joined}
            
            Provide the following analysis in JSON format:
            1. Overall sentiment (positive, negative, or neutral)
            2. Key themes or topics mentioned
            3. Any price predictions or expectations mentioned
            4. Potential risks or opportunities mentioned
            5. Confidence score for your analysis (0-100)
            
            Format your response as valid JSON only.
            """
            
            # Get response from Gemini
            response = self.gemini_model.generate_content(prompt)
            
            try:
                # Extract and parse JSON from response
                response_text = response.text
                # Find JSON content (sometimes Gemini adds explanatory text)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = response_text[json_start:json_end]
                    analysis = json.loads(json_content)
                    logger.info(f"Successfully analyzed {coin} with Gemini AI")
                    return analysis
                else:
                    # If JSON parsing fails, return the raw text
                    return {"raw_analysis": response_text}
            except json.JSONDecodeError:
                logger.warning(f"Could not parse Gemini response as JSON for {coin}")
                return {"raw_analysis": response.text}
                
        except Exception as e:
            logger.error(f"Error using Gemini for {coin} analysis: {e}")
            self.gemini_api_errors[self.current_gemini_api_index] += 1
            
            # Try to rotate and reinitialize if we encounter an error
            if self.gemini_api_errors[self.current_gemini_api_index] >= self.api_rotation_threshold:
                self.get_next_gemini_api_key()
                self._initialize_gemini()
            
            return {}
    
    def analyze_coin_sentiment(self):
        """Analyze sentiment for each coin based on tweet content"""
        for coin in self.coins:
            coin_tweets = [tweet for tweet in self.tweets if coin in tweet.get('text', '')]
            
            # If we have Gemini AI available and enough tweets, use it for analysis
            if self.has_gemini_auth and hasattr(self, 'gemini_model') and len(coin_tweets) >= 3:
                gemini_analysis = self.analyze_with_gemini(coin, coin_tweets)
                if gemini_analysis:
                    self.coins[coin]['ai_analysis'] = gemini_analysis
            
            # Simple sentiment analysis (could be enhanced with NLP libraries)
            positive_words = ['bullish', 'moon', 'pump', 'gains', 'profit', 'buy', 'good', 'great', 'up']
            negative_words = ['bearish', 'dump', 'crash', 'sell', 'down', 'bad', 'scam', 'ponzi']
            
            for tweet in coin_tweets:
                text = tweet.get('text', '').lower()
                pos_count = sum(word in text for word in positive_words)
                neg_count = sum(word in text for word in negative_words)
                
                # Calculate simple sentiment score
                if pos_count > neg_count:
                    self.sentiment_scores[coin].append(1)  # Positive
                elif neg_count > pos_count:
                    self.sentiment_scores[coin].append(-1)  # Negative
                else:
                    self.sentiment_scores[coin].append(0)  # Neutral
            
            # Calculate average sentiment
            if self.sentiment_scores[coin]:
                avg_sentiment = sum(self.sentiment_scores[coin]) / len(self.sentiment_scores[coin])
                self.coins[coin]['sentiment_score'] = avg_sentiment
                self.coins[coin]['sentiment'] = "Positive" if avg_sentiment > 0.2 else "Negative" if avg_sentiment < -0.2 else "Neutral"
                self.coins[coin]['tweet_count'] = len(coin_tweets)
        
        logger.info(f"Completed sentiment analysis for {len(self.coins)} coins")
        return self.coins

    def generate_reports(self):
        """Generate analysis reports"""
        # Generate JSON report
        json_output = os.path.join(self.output_dir, f"coin_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(self.coins, f, indent=2, ensure_ascii=False)
        logger.info(f"Generated JSON report: {json_output}")
        
        # Generate CSV report
        csv_data = []
        for symbol, data in self.coins.items():
            # Extract AI analysis sentiment if available
            ai_sentiment = "N/A"
            ai_confidence = "N/A"
            if 'ai_analysis' in data:
                ai_analysis = data['ai_analysis']
                ai_sentiment = ai_analysis.get('sentiment', "N/A")
                ai_confidence = ai_analysis.get('confidence_score', "N/A")
            
            csv_data.append({
                'Symbol': symbol,
                'Name': data.get('name', 'Unknown'),
                'Mentions': data.get('mentions', 0),
                'Tweet Count': data.get('tweet_count', 0),
                'Sentiment': data.get('sentiment', 'Neutral'),
                'Sentiment Score': data.get('sentiment_score', 0),
                'AI Sentiment': ai_sentiment,
                'AI Confidence': ai_confidence,
                'Price (USD)': data.get('price_usd', 'N/A'),
                'Data Source': data.get('source', 'Unknown'),
                'Analysis Time': data.get('analysis_time', '')
            })
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            csv_output = os.path.join(self.output_dir, f"coin_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            df.to_csv(csv_output, index=False)
            logger.info(f"Generated CSV report: {csv_output}")
            
            # Create simple visualization
            self._generate_visualizations(df)
        
        return json_output
    
    def _generate_visualizations(self, df):
        """Generate visualizations from analysis data"""
        try:
            # Ensure output directory exists
            viz_dir = os.path.join(self.output_dir, 'visualizations')
            if not os.path.exists(viz_dir):
                os.makedirs(viz_dir)
            
            # Top mentioned coins
            plt.figure(figsize=(12, 8))
            top_n = min(15, len(df))
            df_sorted = df.sort_values('Mentions', ascending=False).head(top_n)
            ax = df_sorted.plot.bar(x='Symbol', y='Mentions', color='skyblue')
            plt.title(f'Top {top_n} Mentioned Coins')
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, 'top_mentions.png'))
            plt.close()
            
            # Sentiment distribution
            plt.figure(figsize=(10, 6))
            sentiment_counts = df['Sentiment'].value_counts()
            sentiment_counts.plot.pie(autopct='%1.1f%%', colors=['green', 'red', 'gray'])
            plt.title('Sentiment Distribution')
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, 'sentiment_distribution.png'))
            plt.close()
            
            # Data sources distribution
            plt.figure(figsize=(10, 6))
            if 'Data Source' in df.columns:
                source_counts = df['Data Source'].value_counts()
                source_counts.plot.pie(autopct='%1.1f%%', colors=['blue', 'orange', 'green'])
                plt.title('Data Sources Distribution')
                plt.tight_layout()
                plt.savefig(os.path.join(viz_dir, 'data_sources.png'))
                plt.close()
            
            logger.info(f"Generated visualizations in {viz_dir}")
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")

def main():
    # Initialize analyzer
    analyzer = CoinAnalyzer()
    
    # Load tweet data
    if not analyzer.load_data():
        logger.error("Failed to load tweet data. Exiting.")
        return
    
    # Extract coin symbols from tweets
    analyzer.extract_coin_symbols()
    
    # Fetch details for top mentioned coins
    analyzer.fetch_coin_details()
    
    # Analyze sentiment
    analyzer.analyze_coin_sentiment()
    
    # Generate reports
    report_path = analyzer.generate_reports()
    
    logger.info(f"Analysis complete. Report saved to {report_path}")
    logger.info("Top 10 coin mentions:")
    for coin, count in analyzer.coin_mentions.most_common(10):
        coin_data = analyzer.coins.get(coin, {})
        sentiment = coin_data.get('sentiment', 'Unknown')
        price = coin_data.get('price_usd', 'N/A')
        source = coin_data.get('source', 'Unknown')
        logger.info(f"- {coin}: {count} mentions, Sentiment: {sentiment}, Price: {price}, Source: {source}")

if __name__ == "__main__":
    main() 