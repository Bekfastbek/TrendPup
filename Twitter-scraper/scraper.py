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

    def save_cookies(self):
        try:
            cookies = self.context.cookies()
            with open('twitter_cookies.json', 'w') as f:
                json.dump(cookies, f)
            logger.info("Cookies saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
            return False

    def load_cookies(self):
        try:
            if not os.path.exists('twitter_cookies.json'):
                logger.info("No saved cookies found")
                return False

            with open('twitter_cookies.json', 'r') as f:
                cookies = json.load(f)

            self.context.add_cookies(cookies)
            logger.info("Cookies loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False

    def check_login_status(self):
        try:
            current_url = self.page.url.lower()
            valid_home_urls = ['twitter.com/home', 'x.com/home']

            if any(url in current_url for url in valid_home_urls):
                try:
                    home_selectors = [
                        'div[data-testid="primaryColumn"]',
                        'a[data-testid="AppTabBar_Home_Link"]',
                        'div[data-testid="sidebarColumn"]'
                    ]

                    for selector in home_selectors:
                        if self.page.query_selector(selector):
                            logger.info("Already on home page and verified logged in state")
                            return True

                except Exception as e:
                    logger.warning(f"On home URL but couldn't verify elements: {e}")

            try:
                logger.info("Attempting to load home page...")
                self.page.goto('https://twitter.com/home',
                               timeout = 15000,
                               wait_until = 'domcontentloaded')

                try:
                    self.page.wait_for_selector('''
                        div[data-testid="primaryColumn"],
                        input[autocomplete="username"]
                    ''', timeout = 10000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for page indicators: {e}")

                current_url = self.page.url.lower()

                if any(url in current_url for url in valid_home_urls):
                    try:
                        if self.page.query_selector('div[data-testid="primaryColumn"]'):
                            logger.info("Successfully verified logged in state")
                            return True
                    except Exception:
                        pass

                if self.page.query_selector('input[autocomplete="username"]'):
                    logger.info("Login form detected - not logged in")
                    return False

                if 'login' in current_url or 'signin' in current_url:
                    logger.info("On login page - not logged in")
                    return False

            except Exception as e:
                logger.error(f"Error during home page navigation: {e}")

            try:
                current_url = self.page.url.lower()
                if any(url in current_url for url in valid_home_urls):
                    if self.page.query_selector('div[data-testid="primaryColumn"]'):
                        logger.info("Final check confirms logged in state")
                        return True
            except Exception as e:
                logger.error(f"Error in final state check: {e}")

            logger.info("Could not definitively confirm logged in state")
            return False

        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False

    def login(self):
        try:
            if self.load_cookies() and self.check_login_status():
                return True

            logger.info("Starting login process...")

            try:
                self.page.goto('https://twitter.com/i/flow/login', wait_until = 'domcontentloaded')
                self.page.wait_for_selector('input[autocomplete="username"], div[data-testid="primaryColumn"]')
            except Exception as e:
                logger.error(f"Failed to load login page: {e}")
                return False

            if 'home' in self.page.url.lower():
                logger.info("Redirected to home - already logged in")
                return True

            try:
                logger.info("Entering email...")
                email_input = self.page.wait_for_selector('input[autocomplete="username"]', state = 'visible')
                email_input.fill(self.credentials['email'])
                email_input.press('Tab')

                next_button = self.page.get_by_role("button", name = "Next")
                next_button.click()

                self.page.wait_for_selector('input[data-testid="ocfEnterTextTextInput"], input[name="password"]')
            except Exception as e:
                logger.error(f"Failed at email step: {e}")
                return False

            try:
                username_input = self.page.query_selector('input[data-testid="ocfEnterTextTextInput"]')
                if username_input:
                    logger.info("Username verification required...")
                    username_input.fill(self.credentials['username'])
                    username_input.press('Tab')

                    verify_button = self.page.get_by_role("button", name = "Next")
                    verify_button.click()
                    self.page.wait_for_selector('input[name="password"]')
            except Exception as e:
                logger.info(f"No username verification or error: {e}")

            try:
                logger.info("Entering password...")
                password_input = self.page.wait_for_selector('input[name="password"]', state = 'visible')
                password_input.fill(self.credentials['password'])
                password_input.press('Tab')

                login_button = self.page.get_by_role("button", name = "Log in")
                login_button.click()

                self.page.wait_for_selector(
                    'div[data-testid="primaryColumn"], div[data-testid="error-detail"]'
                )
            except Exception as e:
                logger.error(f"Failed at password step: {e}")
                return False

            try:

                error = self.page.query_selector('div[data-testid="error-detail"]')
                if error:
                    error_text = error.inner_text()
                    logger.error(f"Login error: {error_text}")
                    return False

                if any(url in self.page.url.lower() for url in ['twitter.com/home', 'x.com/home']):
                    logger.info("Successfully logged in!")
                    self.save_cookies()
                    return True
                else:
                    logger.error(f"Login failed - unexpected URL: {self.page.url}")
                    return False

            except Exception as e:
                logger.error(f"Final verification failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Login process failed: {e}")
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
        import platform

        self.playwright = sync_playwright().start()

        launch_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-blink-features=AutomationControlled',
            '--start-maximized',
            '--disable-notifications'
        ]

        if platform.system() == 'Linux':
            is_wsl = 'microsoft' in platform.uname().release.lower()

            if not is_wsl:
                launch_args.extend([
                    '--disable-setuid-sandbox',
                    '--single-process',
                    f'--display={os.environ.get("DISPLAY", ":0")}',
                ])
        else:
            launch_args.append(f'--display={os.environ.get("DISPLAY", ":99")}')

        self.browser = self.playwright.chromium.launch(
            headless = False,
            args = launch_args
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
        retry_count = 0
        total_attempts = 0
        max_retries = 10
        max_total_attempts = 20
        retry_delay = 120

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
                    time.sleep(retry_delay)
                    retry_count = 0
                    self.cleanup()
                    self.setup_browser()
                    if not self.login():
                        raise Exception("Login failed after pause")
                    continue

                logger.info(f"No tweets found for '{query}'. Attempt {retry_count}/{max_retries}. Retrying...")
                time.sleep(2)

            except Exception as e:
                logger.error(f"Scraper error: {e}")
                self.cleanup()
                return []

        logger.warning(f"Giving up on query '{query}' after {total_attempts} total attempts")
        return []


def create_search_queries(scraper):
    return {
        'general': ['new memecoin', 'upcoming memecoin', 'memecoin launch'],
        'trending': ['viral memecoin', 'trending memecoin', 'hot memecoin'],
        'presale': ['memecoin presale', 'token presale', 'new token launch']
    }


def main():
    csv_filename = 'twitter_data.csv'
    try:
        if os.path.exists(csv_filename):
            with open(csv_filename, "w", newline = '', encoding = 'utf-8-sig') as f:
                pass
            logger.info(f"Overriding existing {csv_filename} to start fresh")
    except Exception as e:
        logger.error(f"Error overriding existing CSV file: {e}")

    scraper = TwitterScraper()
    skipped_queries = set()

    try:
        while True:
            try:
                logger.info("Starting new memecoin discovery cycle...")

                queries = create_search_queries(scraper)
                cycle_tweets = []

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

                        if not tweets:
                            skipped_queries.add(term)
                            logger.warning(f"Adding '{term}' to skipped queries")
                        else:
                            for tweet in tweets:
                                tweet['category'] = category
                                tweet['search_term'] = term
                                tweet['discovery_time'] = datetime.now().isoformat()
                            cycle_tweets.extend(tweets)

                        processed_queries += 1
                        time.sleep(2)

                if cycle_tweets:
                    df = pd.DataFrame(cycle_tweets)
                    df.to_csv(csv_filename, mode = 'a', header = not os.path.exists(csv_filename),
                              index = False, encoding = 'utf-8-sig')
                    logger.info(f"Appended {len(cycle_tweets)} tweets to {csv_filename}")

                if processed_queries >= total_queries:
                    if skipped_queries:
                        logger.info(f"Recycling {len(skipped_queries)} previously skipped queries in next cycle")
                        skipped_queries.clear()

                    logger.info("All keywords processed. Waiting for 15 minutes before next cycle...")
                    time.sleep(1800)

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
