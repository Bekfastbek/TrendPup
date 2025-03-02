# test
from playwright.sync_api import sync_playwright
import pandas as pd
import time
import logging
from datetime import datetime
import json
import os

with open('scraper_config.json', 'r') as f:
    config = json.load(f)

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    handlers = [
        logging.FileHandler('twitter_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TwitterScraper:
    def __init__(self):
        self.credentials = {
            'email': config['email'],
            'username': config['username'],
            'password': config['password']
        }
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def login(self):
        try:
            logger.info("Starting login process...")
            self.page.goto('https://twitter.com/i/flow/login')

            self.page.wait_for_load_state('networkidle')

            if "twitter.com/home" in self.page.url or "x.com/home" in self.page.url:
                logger.info("Already logged in!")
                return True

            logger.info("Entering email...")
            email_selector = "input[autocomplete='username']"
            self.page.wait_for_selector(email_selector, state = 'visible', timeout = 5000)
            self.page.fill(email_selector, self.credentials['email'])

            next_button = self.page.get_by_role("button", name = "Next")
            next_button.click()

            username_verify_selector = "input[data-testid='ocfEnterTextTextInput']"
            if self.page.wait_for_selector(username_verify_selector, timeout = 5000, state = 'visible'):
                logger.info("Username verification required...")
                self.page.fill(username_verify_selector, self.credentials['username'])
                self.page.get_by_role("button", name = "Next").click()

            logger.info("Entering password...")
            password_selector = "input[name='password']"
            self.page.wait_for_selector(password_selector, state = 'visible', timeout = 5000)
            self.page.fill(password_selector, self.credentials['password'])

            login_button = self.page.get_by_role("button", name = "Log in")
            login_button.click()

            self.page.wait_for_load_state('networkidle')

            time.sleep(3)

            max_attempts = 5
            for attempt in range(max_attempts):
                if "twitter.com/home" in self.page.url or "x.com/home" in self.page.url:
                    logger.info("Successfully logged in!")
                    return True
                logger.info(f"Waiting for home page... Attempt {attempt + 1}/{max_attempts}")
                time.sleep(2)

            logger.error(f"Login might have failed. Current URL: {self.page.url}")
            return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            if "twitter.com/home" in self.page.url or "x.com/home" in self.page.url:
                logger.info("Successfully logged in despite errors!")
                return True
            return False

    def extract_tweet_data(self, tweet):
        try:
            tweet_data = {}

            user_name_element = tweet.query_selector('div[data-testid="User-Name"]')
            if user_name_element:
                name_texts = user_name_element.inner_text().split('\n')
                tweet_data['username'] = name_texts[0] if len(name_texts) > 0 else ''
                tweet_data['handle'] = name_texts[1] if len(name_texts) > 1 else ''

            text_element = tweet.query_selector('div[data-testid="tweetText"]')
            tweet_data['text'] = text_element.inner_text() if text_element else ''

            time_element = tweet.query_selector('time')
            tweet_data['timestamp'] = time_element.get_attribute('datetime') if time_element else ''

            for metric in ['reply', 'retweet', 'like']:
                metric_element = tweet.query_selector(f'div[data-testid="{metric}"]')
                tweet_data[f'{metric}_count'] = self.parse_metric(
                    metric_element.inner_text() if metric_element else '0')

            link_element = tweet.query_selector('a[href*="/status/"]')
            if link_element:
                tweet_data['url'] = f"https://twitter.com{link_element.get_attribute('href')}"

            return tweet_data

        except Exception as e:
            logger.error(f"Error extracting tweet data: {e}")
            return None

    def parse_metric(self, metric_text):
        try:
            if not metric_text:
                return 0
            metric_text = metric_text.upper().strip()
            if 'K' in metric_text:
                return int(float(metric_text.replace('K', '')) * 1000)
            elif 'M' in metric_text:
                return int(float(metric_text.replace('M', '')) * 1000000)
            return int(metric_text)
        except:
            return 0

    def scrape_tweets(self, query = "", max_tweets = 100, scroll_pause_time = 2):
        tweets_data = []
        seen_tweets = set()
        scroll_attempts = 0
        max_scroll_attempts = 10
        no_new_tweets_count = 0
        max_no_new_tweets = 3

        try:
            if query:
                encoded_query = query.replace(' ', '%20')
                self.page.goto(f'https://twitter.com/search?q={encoded_query}&f=live')
            else:
                self.page.goto('https://twitter.com/home')

            logger.info("Waiting for tweets to load...")
            time.sleep(5)

            previous_tweets_count = 0
            while len(tweets_data) < max_tweets and scroll_attempts < max_scroll_attempts:
                logger.info(f"Found {len(tweets_data)} tweets so far...")

                tweets = self.page.query_selector_all('article[data-testid="tweet"]')

                for tweet in tweets:
                    tweet_data = self.extract_tweet_data(tweet)

                    if tweet_data and tweet_data.get('url') not in seen_tweets:
                        seen_tweets.add(tweet_data['url'])
                        tweets_data.append(tweet_data)

                if len(tweets_data) == previous_tweets_count:
                    no_new_tweets_count += 1
                    if no_new_tweets_count >= max_no_new_tweets:
                        logger.info("No new tweets found after multiple scrolls, stopping...")
                        break
                else:
                    no_new_tweets_count = 0

                previous_tweets_count = len(tweets_data)

                self.page.evaluate('window.scrollBy(0, 1000)')
                time.sleep(scroll_pause_time)
                scroll_attempts += 1

            return tweets_data

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return tweets_data

    def save_results(self, tweets_data):
        if not tweets_data:
            logger.warning("No tweets to save")
            return

        try:
            df = pd.DataFrame(tweets_data)
            csv_filename = 'twitter_data.csv'
            df.to_csv(csv_filename, mode = 'a', header = not os.path.exists(csv_filename),
                      index = False, encoding = 'utf-8-sig')
            logger.info(f"Appended {len(tweets_data)} tweets to {csv_filename}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

    def run(self, query = "", max_tweets = 100):
        """Run method with XVFB support"""
        try:
            if not self.browser:
                self.playwright = sync_playwright().start()

                # Launch with display settings for XVFB
                self.browser = self.playwright.chromium.launch(
                    headless = False,  # We're using XVFB so set this to False
                    args = [
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        f'--display={os.environ.get("DISPLAY", ":99")}',  # Use XVFB display
                        '--disable-blink-features=AutomationControlled',
                        '--start-maximized',
                        '--disable-notifications'
                    ]
                )

                self.context = self.browser.new_context(
                    viewport = {'width': 1920, 'height': 1080},
                    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    has_touch = True,
                    is_mobile = False,
                    locale = 'en-US',
                    timezone_id = 'Europe/London',
                )

                # Add stealth scripts
                self.context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """)

                self.page = self.context.new_page()

                if not self.login():
                    raise Exception("Login failed")

            tweets = self.scrape_tweets(query = query, max_tweets = max_tweets)
            return tweets

        except Exception as e:
            logger.error(f"Scraper error: {e}")
            self.cleanup()
            return []


def create_base_patterns():
    """Create base search patterns focused on finding new memecoins"""
    return {
        "new_launches": [
            "stealth launch {}",
            "just launched {}",
            "new {} token",
            "new {} coin",
            "{} fair launch",
            "{} first hour",
            "launching {} token",
            "{} stealth",
            "{} presale live",
            "{} contract deployed"
        ],
        "trending_coins": [
            "{} trending",
            "{} mooning",
            "{} pumping",
            "ape {} token",
            "{} next 100x",
            "{} gem found",
            "{} launching soon",
            "{} just listed",
            "{} liquidity added",
            "{} dexscreener"
        ]
    }


def get_initial_memecoin_candidates(scraper, max_tweets = 100):
    """Find potential new memecoin launches and mentions"""
    # Multiple search queries to cast a wide net
    search_queries = [
        "new stealth launch coin -is:retweet min_faves:10",
        "just launched token memecoin -is:retweet min_faves:5",
        "new memecoin contract deployed -is:retweet",
        "stealth launching now -is:retweet min_faves:5",
        "first block buyers -is:retweet",
        "contract deploying memecoin -is:retweet"
    ]

    all_coins = set()

    for query in search_queries:
        logger.info(f"Searching for potential coins with query: {query}")
        tweets = scraper.run(query = query, max_tweets = max_tweets // len(search_queries))

        for tweet in tweets:
            text = tweet.get('text', '').lower()

            # Extract potential coin names
            words = text.split()
            for i, word in enumerate(words):
                # Look for cashtags
                if word.startswith('$') and len(word) > 1:
                    coin = word[1:].upper()
                    if len(coin) >= 3:  # Avoid too short symbols
                        all_coins.add(coin)

                # Look for contract addresses (basic validation)
                if word.startswith('0x') and len(word) == 42:
                    # Store contract address as potential identifier
                    all_coins.add(word)

                # Look for words before specific indicators
                if i > 0 and word in ['token', 'coin', 'memecoin', 'launch']:
                    potential_name = words[i - 1].strip('.,!?#@').upper()
                    if len(potential_name) >= 3:
                        all_coins.add(potential_name)

    logger.info(f"Found {len(all_coins)} potential new coins")
    return list(all_coins)


def validate_coin(scraper, coin):
    """Basic validation of a potential coin"""
    # Search for recent mentions of this coin
    query = f'"{coin}" (memecoin OR token OR launch) -is:retweet'
    tweets = scraper.run(query = query, max_tweets = 10)

    if not tweets:
        return False

    # Check if tweets are recent (within last 24 hours)
    current_time = datetime.now()
    for tweet in tweets:
        tweet_time = datetime.fromisoformat(tweet.get('timestamp', '').replace('Z', '+00:00'))
        if (current_time - tweet_time).days < 1:
            return True

    return False


def create_search_queries(scraper):
    """Generate focused queries for new memecoin discovery"""
    coins = get_initial_memecoin_candidates(scraper)
    validated_coins = []

    logger.info("Validating discovered coins...")
    for coin in coins:
        if validate_coin(scraper, coin):
            validated_coins.append(coin)

    logger.info(f"Validated {len(validated_coins)} coins out of {len(coins)} candidates")

    # Generate specific queries for validated coins
    queries = {}
    base_patterns = create_base_patterns()

    for category, patterns in base_patterns.items():
        queries[category] = []
        for coin in validated_coins:
            for pattern in patterns:
                query = pattern.format(coin)
                # Add filters to ensure quality results
                query = f'{query} lang:en -is:retweet min_faves:2'
                queries[category].append(query)

    return queries


def main():
    # Delete existing CSV file when starting a new instance
    csv_filename = 'new_memecoins.csv'
    try:
        if os.path.exists(csv_filename):
            os.remove(csv_filename)
            logger.info(f"Deleted existing {csv_filename} to start fresh")
    except Exception as e:
        logger.error(f"Error deleting existing CSV file: {e}")

    scraper = TwitterScraper()

    try:
        # Run continuous monitoring
        while True:
            try:
                logger.info("Starting new memecoin discovery cycle...")

                # Get fresh queries based on recent activity
                queries = create_search_queries(scraper)

                cycle_tweets = []
                for category, search_terms in queries.items():
                    for term in search_terms:
                        logger.info(f"Searching: {term}")
                        tweets = scraper.run(query = term, max_tweets = 50)

                        for tweet in tweets:
                            tweet['category'] = category
                            tweet['search_term'] = term
                            tweet['discovery_time'] = datetime.now().isoformat()

                        cycle_tweets.extend(tweets)
                        time.sleep(2)  # Rate limiting between queries

                # Save results for this cycle
                if cycle_tweets:
                    df = pd.DataFrame(cycle_tweets)
                    df.to_csv(csv_filename, mode = 'a', header = not os.path.exists(csv_filename),
                              index = False, encoding = 'utf-8-sig')
                    logger.info(f"Appended {len(cycle_tweets)} tweets to {csv_filename}")

                logger.info("Waiting for next discovery cycle...")
                time.sleep(300)  # 5 minutes between cycles

            except Exception as e:
                logger.error(f"Error in discovery cycle: {e}")
                time.sleep(60)  # Wait a minute before retrying

    except KeyboardInterrupt:
        logger.info("Received shutdown signal. Cleaning up...")
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
