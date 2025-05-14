import os
import asyncio
import logging
import snscrape.modules.twitter as sntwitter
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TwitterWatcher:
    def __init__(self, usernames_str: str, poll_interval: int):
        if not usernames_str:
            raise ValueError("Twitter usernames string cannot be empty.")
        self.usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
        if not self.usernames:
            raise ValueError("No valid Twitter usernames provided after stripping and splitting.")
        self.poll_interval = poll_interval
        self.seen_tweet_ids = {username: set() for username in self.usernames}
        self.last_check_time = {username: datetime.now(timezone.utc) for username in self.usernames}

        # Initialize seen_tweet_ids with recent tweets to avoid processing old ones on first run
        # For simplicity, we'll fetch a few recent tweets for each user and mark them as seen.
        # A more robust solution might involve persistent storage of seen IDs.
        logger.info(f"Initializing TwitterWatcher for users: {self.usernames}")
        # asyncio.run(self._initialize_seen_tweets()) # Cannot run async in constructor, will do it in main or first watch call

    async def _initialize_seen_tweets(self, username):
        """Fetches a few recent tweets to initialize the seen_tweet_ids set for a user."""
        try:
            logger.info(f"Initializing seen tweets for @{username}...")
            # Query for tweets from the specific user, sort by date, take top N
            # snscrape query format for user: 'from:username'
            query = f"from:{username}"
            scraper = sntwitter.TwitterUserScraper(username)
            count = 0
            for i, tweet in enumerate(scraper.get_items()):
                if i >= 5: # Initialize with last 5 tweets
                    break
                self.seen_tweet_ids[username].add(tweet.id)
                count += 1
            logger.info(f"Initialized @{username} with {count} recent tweets marked as seen.")
            self.last_check_time[username] = datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Error initializing seen tweets for @{username}: {e}")

    async def watch(self):
        """Asynchronously yields new tweets from the specified users."""
        # Initialize all users first
        for username in self.usernames:
            if not self.seen_tweet_ids[username]: # only if not already initialized
                 await self._initialize_seen_tweets(username)

        while True:
            for username in self.usernames:
                logger.info(f"Checking for new tweets from @{username} since {self.last_check_time[username].isoformat()}...")
                new_tweets_for_user = []
                try:
                    # snscrape query for user: 'from:username since:YYYY-MM-DD'
                    # We'll fetch tweets and filter by date client-side as 'since_id' is not directly supported for user timelines in a simple way
                    # and 'since' date might miss tweets if polling is infrequent.
                    # A better approach is to get N recent tweets and check against seen_tweet_ids.
                    scraper = sntwitter.TwitterUserScraper(username)
                    current_fetch_time = datetime.now(timezone.utc)
                    temp_tweets = []
                    for i, tweet in enumerate(scraper.get_items()):
                        if i >= 20: # Check last 20 tweets to be safe
                            break
                        if tweet.id not in self.seen_tweet_ids[username] and tweet.date > self.last_check_time[username]:
                            # Basic tweet object, can be expanded
                            simple_tweet = {
                                'id': tweet.id,
                                'username': tweet.user.username,
                                'content': tweet.rawContent, # or .renderedContent
                                'url': tweet.url,
                                'date': tweet.date
                            }
                            temp_tweets.append(simple_tweet)
                    
                    # Sort by date to process in chronological order
                    temp_tweets.sort(key=lambda t: t['date'])

                    for tweet_data in temp_tweets:
                        if tweet_data['id'] not in self.seen_tweet_ids[username]:
                            new_tweets_for_user.append(tweet_data)
                            self.seen_tweet_ids[username].add(tweet_data['id'])
                            logger.info(f"New tweet from @{username}: {tweet_data['id']} - {tweet_data['content'][:50]}...")
                            yield tweet_data # Yield one tweet at a time

                    self.last_check_time[username] = current_fetch_time 

                except Exception as e:
                    logger.error(f"Error fetching tweets for @{username}: {e}")
            
            logger.info(f"Waiting for {self.poll_interval} seconds before next check...")
            await asyncio.sleep(self.poll_interval)

# Example Usage (for testing purposes, will be integrated into main.py)
async def _test_watcher():
    logging.basicConfig(level=logging.INFO)
    # Simulate loading from .env
    test_usernames = "elonmusk,VitalikButerin" # Using a different second user for testing
    test_poll_interval = 30 # seconds

    watcher = TwitterWatcher(usernames_str=test_usernames, poll_interval=test_poll_interval)
    
    try:
        async for tweet in watcher.watch():
            logger.info(f"[TEST HANDLER] Received tweet: ID={tweet['id']}, User={tweet['username']}, Content='{tweet['content'][:100]}...' URL={tweet['url']}")
    except KeyboardInterrupt:
        logger.info("Test watcher stopped by user.")
    except Exception as e:
        logger.error(f"Error in test watcher: {e}")

if __name__ == "__main__":
    # To run this test, you might need to install snscrape: pip install snscrape
    # Also, ensure you are in an environment where asyncio.run() can be called.
    # This is a basic test and might not cover all edge cases.
    asyncio.run(_test_watcher())

