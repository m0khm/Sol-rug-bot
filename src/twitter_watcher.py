#src/twitter_watcher.py
import os
import time
import logging
import tweepy
from tweepy.errors import TooManyRequests

class TwitterWatcher:
    """
    Стримит твиты сразу нескольких пользователей через v2 Filtered Stream.
    """

    def __init__(self, bearer_token: str, usernames: list[str]):
        self.client = tweepy.Client(bearer_token=bearer_token)
        self.usernames = [u.strip() for u in usernames if u.strip()]
        if not self.usernames:
            raise ValueError("Укажите хотя бы одного пользователя в WATCH_TWITTER_USERS")

        self.user_ids = []
        self.id_to_username = {}
        for username in self.usernames:
            uid = self._get_user_id_with_retry(username)
            self.user_ids.append(uid)
            self.id_to_username[uid] = username

    def _get_user_id_with_retry(self, username: str) -> str:
        """ Получаем user_id с экспоненциальным бэкоффом при 429 """
        while True:
            try:
                user = self.client.get_user(username=username)
                return user.data.id
            except TooManyRequests as e:
                reset_ts = int(e.response.headers.get("x-rate-limit-reset", time.time() + 60))
                wait = max(reset_ts - time.time(), 30)
                logging.warning(f"Rate limit for {username}, спим {wait:.0f}s")
                time.sleep(wait)

    def stream_tweets(self):
        """ Генератор новых твитов """
        stream = tweepy.StreamingClient(
            bearer_token=self.client.bearer_token,
            wait_on_rate_limit=True
        )

        # очистим старые правила
        existing = stream.get_rules().data or []
        if existing:
            stream.delete_rules([r.id for r in existing])

        # добавим новое правило "from:id1 OR from:id2 OR …"
        rule = " OR ".join(f"from:{uid}" for uid in self.user_ids)
        stream.add_rules(tweepy.StreamRule(value=rule))

        for tweet in stream.filter(tweet_fields=["author_id", "id", "text"]):
            yield {
                "id": tweet.id,
                "text": tweet.text,
                "author_username": self.id_to_username.get(tweet.author_id, str(tweet.author_id))
            }

