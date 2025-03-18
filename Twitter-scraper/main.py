#!/usr/bin/env python3
import os
import time
import subprocess
import logging
import threading
import signal
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

class TwitterDataHandler(FileSystemEventHandler):
    def __init__(self, analyzer_path):
        self.analyzer_path = analyzer_path
        self.last_modified = time.time()
        self.cooldown = 5

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('twitter_data.json'):
            current_time = time.time()
            if current_time - self.last_modified > self.cooldown:
                self.last_modified = current_time
                logger.info(f"Detected change to {event.src_path}")
                logger.info("Waiting 5 seconds to ensure file is fully written...")
                time.sleep(5)
                
                logger.info("Starting coin analyzer...")
                try:
                    result = subprocess.run(['python3', self.analyzer_path], 
                                           capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("Analysis completed successfully")
                    else:
                        logger.error(f"Analysis failed with error: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error running analyzer: {e}")

class TwitterPipeline:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.scraper_path = os.path.join(self.base_dir, 'scraper.py')
        self.analyzer_path = os.path.join(self.base_dir, 'coin_analyzer.py')
        self.data_file = os.path.join(self.base_dir, 'twitter_data.json')
        self.xvfb_process = None
        self.scraper_process = None
        self.observer = None
        self.running = False
    
    def setup_xvfb(self):
        """Set up Xvfb display for headless browser"""
        logger.info("Setting up Xvfb display...")
        
        # Kill any existing Xvfb processes
        try:
            subprocess.run(['pkill', 'Xvfb'], check=False)
        except Exception:
            pass
        
        # Start Xvfb
        try:
            self.xvfb_process = subprocess.Popen(
                ['Xvfb', ':99', '-screen', '0', '1920x1080x24'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            os.environ['DISPLAY'] = ':99'
            time.sleep(2)  # Give Xvfb time to start
            logger.info("Xvfb started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start Xvfb: {e}")
            return False
    
    def start_scraper(self):
        """Start the Twitter scraper in a separate process"""
        logger.info("Starting Twitter scraper...")
        try:
            self.scraper_process = subprocess.Popen(
                ['python3', self.scraper_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info("Scraper started successfully")
            
            # Start a thread to monitor scraper output
            threading.Thread(target=self._monitor_scraper_output, daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"Failed to start scraper: {e}")
            return False
    
    def _monitor_scraper_output(self):
        """Monitor and log the scraper's output"""
        for line in self.scraper_process.stdout:
            logger.info(f"Scraper: {line.strip()}")
        for line in self.scraper_process.stderr:
            logger.error(f"Scraper error: {line.strip()}")
    
    def start_file_watcher(self):
        """Start watching twitter_data.json for changes"""
        logger.info("Starting file watcher...")
        
        # Check if twitter_data.json exists, create it if it doesn't
        if not os.path.exists(self.data_file):
            logger.info(f"Creating empty {self.data_file}")
            with open(self.data_file, 'w') as f:
                f.write('[]')
        
        # Set up the file watcher
        event_handler = TwitterDataHandler(self.analyzer_path)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.base_dir, recursive=False)
        self.observer.start()
        logger.info("File watcher started successfully")
        return True
    
    def start(self):
        """Start the entire Twitter pipeline"""
        logger.info("Starting Twitter pipeline...")
        self.running = True
        
        # Set up Xvfb
        if not self.setup_xvfb():
            logger.error("Failed to set up Xvfb. Exiting.")
            return False
        
        # Start the scraper
        if not self.start_scraper():
            logger.error("Failed to start scraper. Exiting.")
            self.cleanup()
            return False
        
        # Start the file watcher
        if not self.start_file_watcher():
            logger.error("Failed to start file watcher. Exiting.")
            self.cleanup()
            return False
        
        logger.info("Twitter pipeline started successfully")
        return True
    
    def stop(self):
        """Stop the entire Twitter pipeline"""
        logger.info("Stopping Twitter pipeline...")
        self.running = False
        
        # Stop the file watcher
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.cleanup()
        logger.info("Twitter pipeline stopped")
    
    def cleanup(self):
        """Clean up processes and resources"""
        # Kill the scraper process
        if self.scraper_process:
            logger.info("Terminating scraper process...")
            self.scraper_process.terminate()
            try:
                self.scraper_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.scraper_process.kill()
        
        # Kill Xvfb
        if self.xvfb_process:
            logger.info("Terminating Xvfb process...")
            self.xvfb_process.terminate()
            try:
                self.xvfb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.xvfb_process.kill()
        
        # Additional cleanup
        try:
            subprocess.run(['pkill', 'Xvfb'], check=False)
        except Exception:
            pass

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal. Shutting down...")
    if pipeline and pipeline.running:
        pipeline.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the pipeline
    pipeline = TwitterPipeline()
    if pipeline.start():
        # Keep the main thread alive
        try:
            while pipeline.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down...")
            pipeline.stop()
    else:
        logger.error("Failed to start Twitter pipeline.")
        sys.exit(1) 