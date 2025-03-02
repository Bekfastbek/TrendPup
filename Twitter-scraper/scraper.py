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

    def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None

    def scrape_tweets(self, query = "", max_tweets = 100, scroll_pause_time = 2, retry_attempt = 1,
                      max_retries = 10):
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
                logger.info(f"Found {len(tweets_data)} tweets so far... (Attempt {retry_attempt})")

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

    def setup_browser(self):
        """Extract browser setup logic from run method"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless = False,
            args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                f'--display={os.environ.get("DISPLAY", ":99")}',
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

        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
        """)

        self.page = self.context.new_page()

    def run(self, query = "", max_tweets = 100):
        """Run method with retry logic and rate limit handling"""
        retry_count = 0
        total_attempts = 0
        max_retries = 10
        max_total_attempts = 20  # Total maximum attempts (2 sets of 10 tries)
        retry_delay = 900  # 15 minutes in seconds

        while total_attempts < max_total_attempts:
            try:
                if not self.browser:
                    self.setup_browser()
                    if not self.login():
                        raise Exception("Login failed")

                tweets = self.scrape_tweets(query = query, max_tweets = max_tweets, retry_attempt = retry_count + 1)

                if tweets:
                    return tweets

                retry_count += 1
                total_attempts += 1

                if retry_count >= max_retries:
                    logger.warning(
                        f"No tweets found for '{query}' after {retry_count} attempts. Pausing for 15 minutes...")
                    time.sleep(retry_delay)  # 15 minutes pause
                    retry_count = 0  # Reset retry counter for second set of attempts
                    # Refresh the browser session after the pause
                    self.cleanup()
                    self.setup_browser()
                    if not self.login():
                        raise Exception("Login failed after pause")
                    continue

                logger.info(f"No tweets found for '{query}'. Attempt {retry_count}/{max_retries}. Retrying...")
                time.sleep(2)  # Short delay between retries

            except Exception as e:
                logger.error(f"Scraper error: {e}")
                self.cleanup()
                return []

        logger.warning(f"Giving up on query '{query}' after {total_attempts} total attempts")
        return []


def create_search_queries(scraper):
    """Create search queries for memecoin discovery"""
    return {
        'general': ['new memecoin', 'upcoming memecoin', 'memecoin launch'],
        'trending': ['viral memecoin', 'trending memecoin', 'hot memecoin'],
        'presale': ['memecoin presale', 'token presale', 'new token launch']
    }


def main():
    # Delete existing CSV file when starting a new instance
    csv_filename = 'twitter_data.csv'
    try:
        if os.path.exists(csv_filename):
            os.remove(csv_filename)
            logger.info(f"Deleted existing {csv_filename} to start fresh")
    except Exception as e:
        logger.error(f"Error deleting existing CSV file: {e}")

    scraper = TwitterScraper()
    skipped_queries = set()  # Track skipped queries for recycling

    try:
        while True:
            try:
                logger.info("Starting new memecoin discovery cycle...")

                # Get fresh queries based on recent activity
                queries = create_search_queries(scraper)
                cycle_tweets = []

                # Calculate total queries excluding previously skipped ones
                active_queries = {
                    category: [term for term in terms if term not in skipped_queries]
                    for category, terms in queries.items()
                }
                total_queries = sum(len(terms) for terms in active_queries.values())
                processed_queries = 0

                for category, search_terms in active_queries.items():
                    for term in search_terms:
                        logger.info(f"Searching: {term} ({processed_queries + 1}/{total_queries})")

                        tweets = scraper.run(query = term, max_tweets = 50)

                        if not tweets:  # If no tweets found after all retries
                            skipped_queries.add(term)
                            logger.warning(f"Adding '{term}' to skipped queries")
                        else:
                            for tweet in tweets:
                                tweet['category'] = category
                                tweet['search_term'] = term
                                tweet['discovery_time'] = datetime.now().isoformat()
                            cycle_tweets.extend(tweets)

                        processed_queries += 1
                        time.sleep(2)  # Rate limiting between queries

                # Save results for this cycle
                if cycle_tweets:
                    df = pd.DataFrame(cycle_tweets)
                    df.to_csv(csv_filename, mode = 'a', header = not os.path.exists(csv_filename),
                              index = False, encoding = 'utf-8-sig')
                    logger.info(f"Appended {len(cycle_tweets)} tweets to {csv_filename}")

                # If we've processed all available queries
                if processed_queries >= total_queries:
                    if skipped_queries:
                        logger.info(f"Recycling {len(skipped_queries)} previously skipped queries in next cycle")
                        skipped_queries.clear()  # Clear skipped queries to try them again in next cycle

                    logger.info("All keywords processed. Waiting for 15 minutes before next cycle...")
                    time.sleep(900)  # Wait 15 minutes before starting new cycle

            except Exception as e:
                logger.error(f"Error in discovery cycle: {e}")
                logger.info("Waiting for 60 seconds before retrying...")
                time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal. Cleaning up...")
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
