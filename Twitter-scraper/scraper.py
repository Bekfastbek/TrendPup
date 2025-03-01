import email

from playwright.sync_api import sync_playwright
import pandas as pd
import time
import logging
from datetime import datetime
import json

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

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            df = pd.DataFrame(tweets_data)
            csv_filename = f'twitter_data_{timestamp}.csv'
            df.to_csv(csv_filename, index = False, encoding = 'utf-8-sig')
            logger.info(f"Saved {len(tweets_data)} tweets to {csv_filename}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

        try:
            json_filename = f'twitter_data_{timestamp}.json'
            with open(json_filename, 'w', encoding = 'utf-8') as f:
                json.dump(tweets_data, f, ensure_ascii = False, indent = 2)
            logger.info(f"Saved tweets to {json_filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")

    def run(self, query = "", max_tweets = 100):
        try:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(
                headless = False,
                args = [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features',
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized'
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

            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            self.page = self.context.new_page()

            if not self.login():
                raise Exception("Login failed")

            tweets = self.scrape_tweets(query, max_tweets)

            self.save_results(tweets)

            self.context.close()
            self.browser.close()
            playwright.stop()

            return tweets

        except Exception as e:
            logger.error(f"Scraper error: {e}")
            return []

        finally:
            try:
                if hasattr(self, 'context') and self.context:
                    self.context.close()
                if hasattr(self, 'browser') and self.browser:
                    self.browser.close()
                if 'playwright' in locals():
                    playwright.stop()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


def create_search_queries():
    queries = {
        "stealth_launch": [
            "new Injective memecoin"
            "coin",
            "stealth launch Injective",
            "just launched on Injective",
            "Injective memecoin"
            "coin presale",
            "Injective degen launch",
            "Injective low cap memecoin"
            "coin",
            "first hour Injective",
            "Injective microcap gem",
            "Injective launchpad memecoin"
            "coin",
            "Injective fair launch",
            "Injective 100x memecoin"
            "coin"
        ],
        "organic_shilling": [
            "under the radar Injective",
            "hidden gem Injective",
            "Injective memecoin"
            "coin going viral",
            "Injective small cap moon",
            "Injective next dog coin",
            "Injective next 100x",
            "Injective early entry",
            "Injective memecoin"
            " sniper",
            "Injective low market cap",
            "Injective moonbag"
        ],
        "whale_tracking": [
            "Injective whales buying",
            "Injective memecoin"
            " smart money",
            "Injective memecoin"
            " sniper alert",
            "Injective memecoin"
            " accumulation",
            "Injective memecoin"
            " pre-pump",
            "Injective memecoin"
            " first buyers",
            "Injective memecoin"
            " 10x soon",
            "Injective early adopter"
        ],
        "memecoin"
        "_specific": [
            "Injective dog coin",
            "Injective cat coin",
            "Injective pepe token",
            "Injective frog coin",
            "Injective degen coin",
            "Injective viral memecoin"
            "",
            "Injective moon mission",
            "Injective joke coin"
        ],
        "trading_signals": [
            "Injective memecoin"
            " coin liquidity added",
            "Injective memecoin"
            " coin breakout soon",
            "Injective memecoin"
            " volume spike",
            "Injective memecoin"
            " accumulation",
            "Injective memecoin"
            " coin dexscreener",
            "Injective memecoin"
            " whales loading up",
            "Injective memecoin"
            " coin first buys"
        ]
    }
    return queries


def main():
    scraper = TwitterScraper()
    all_tweets = []
    queries = create_search_queries()

    all_search_terms = []
    for category, terms in queries.items():
        all_search_terms.extend([(term, category) for term in terms])

    total_terms = len(all_search_terms)
    tweets_per_term = 100 // total_terms

    logger.info(f"Processing {total_terms} search terms, aiming for {tweets_per_term} tweets per term")

    for term, category in all_search_terms:
        # Create search query with filters
        search_query = f'"{term}" lang:en -is:retweet'
        logger.info(f"\nSearching for: {search_query}")

        tweets = scraper.run(query = search_query, max_tweets = tweets_per_term)

        for tweet in tweets:
            tweet['category'] = category
            tweet['search_term'] = term

        all_tweets.extend(tweets)
        logger.info(f"Found {len(tweets)} tweets for term: {term}")
        time.sleep(3)

        if len(all_tweets) > 0 and (all_search_terms.index((term, category)) + 1) % 10 == 0:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            intermediate_filename = f'twitter_data_intermediate_{timestamp}.csv'
            pd.DataFrame(all_tweets).to_csv(intermediate_filename, index = False, encoding = 'utf-8-sig')
            logger.info(f"Saved intermediate results ({len(all_tweets)} tweets) to {intermediate_filename}")

    if all_tweets:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            df = pd.DataFrame(all_tweets)
            csv_filename = f'twitter_data_final_{timestamp}.csv'
            df.to_csv(csv_filename, index = False, encoding = 'utf-8-sig')
            logger.info(f"Saved {len(all_tweets)} tweets to {csv_filename}")
            category_stats = df.groupby('category').agg({
                'search_term': 'count'
            }).rename(columns = {'search_term': 'tweet_count'})
            logger.info("\nTweets per category:")
            logger.info(category_stats)

        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

        try:
            json_filename = f'twitter_data_final_{timestamp}.json'
            metadata = {
                'timestamp': timestamp,
                'total_tweets': len(all_tweets),
                'categories': {
                    category: {
                        'total_tweets': len([t for t in all_tweets if t['category'] == category]),
                        'terms_used': list(set(t['search_term'] for t in all_tweets if t['category'] == category))
                    }
                    for category in queries.keys()
                }
            }

            with open(json_filename, 'w', encoding = 'utf-8') as f:
                json.dump({
                    'metadata': metadata,
                    'tweets': all_tweets
                }, f, ensure_ascii = False, indent = 2)
            logger.info(f"Saved tweets to {json_filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")

        logger.info(f"\nScraping completed successfully:")
        logger.info(f"Total tweets collected: {len(all_tweets)}")
        logger.info(f"Average tweets per search term: {len(all_tweets) / total_terms:.2f}")
    else:
        logger.error("Scraping failed - no tweets collected")


if __name__ == "__main__":
    main()

