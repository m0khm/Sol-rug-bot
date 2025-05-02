# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator, Dict
import tweepy
from tweepy.errors import TooManyRequests

class TwitterWatcher:
    """
    Async-генератор новых твитов для нескольких user_id за один запрос.
    Использует search_recent_tweets с общей since_id.
    """

    def __init__(self, bearer_token: str, poll_interval: int = 60, max_results: int = 100):
        self.client = tweepy.Client(bearer_token=bearer_token)

        # Читаем из .env
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        raw_ids   = os.getenv("WATCH_TWITTER_USER_IDS", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        self.user_ids   = [i.strip() for i in raw_ids.split(",")   if i.strip()]

        if len(self.usernames) != len(self.user_ids) or not self.user_ids:
            raise ValueError("WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS должны совпадать и быть непустыми")

        self.id_to_username: Dict[str,str] = dict(zip(self.user_ids, self.usernames))
        self.query = " OR ".join(f"from:{uid}" for uid in self.user_ids)

        # Global since_id для всего поиска
        self.since_id: str | None = None
        self.poll_interval = poll_interval
        self.max_results = max_results

    async def stream_tweets(self) -> AsyncGenerator[Dict, None]:
        """
        Async-генератор:
         - каждую poll_interval сек делает 1 запрос search_recent_tweets
         - отдаёт по одному новым твитам от любого из user_ids
        """
        while True:
            try:
                resp = await asyncio.to_thread(
                    self.client.search_recent_tweets,
                    query=self.query,
                    since_id=self.since_id,
                    tweet_fields=["author_id", "id", "text"],
                    max_results=self.max_results
                )
            except TooManyRequests as e:
                reset_ts = int(e.response.headers.get("x-rate-limit-reset", asyncio.get_event_loop().time() + 60))
                wait = max(reset_ts - asyncio.get_event_loop().time(), 30)
                logging.warning(f"Rate limit hit, sleeping {wait:.0f}s")
                await asyncio.sleep(wait)
                continue

            tweets = resp.data or []
            # сортируем по возрастанию ID, чтобы выдавать в хронологическом порядке
            tweets.sort(key=lambda t: t.id)

            for t in tweets:
                # обновляем since_id
                if self.since_id is None or t.id > int(self.since_id):
                    self.since_id = str(t.id)
                yield {
                    "id":               t.id,
                    "text":             t.text,
                    "author_username":  self.id_to_username.get(str(t.author_id), str(t.author_id))
                }

            await asyncio.sleep(self.poll_interval)
