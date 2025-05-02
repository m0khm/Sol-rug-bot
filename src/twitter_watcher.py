# src/twitter_watcher.py

import os
import asyncio
from typing import AsyncGenerator, Dict
import logging
import tweepy

class TwitterWatcher:
    """
    Периодически опрашивает endpoint users/:id/tweets 
    вместо Filtered Stream (для free-tier Twitter API v2).
    """

    def __init__(self, bearer_token: str, poll_interval: int = 60):
        self.client = tweepy.Client(bearer_token=bearer_token)
        # читаем из .env
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        raw_ids   = os.getenv("WATCH_TWITTER_USER_IDS", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        self.user_ids   = [i.strip() for i in raw_ids.split(",")   if i.strip()]
        if len(self.usernames) != len(self.user_ids):
            raise ValueError("WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS должны быть одинаковой длины")
        self.id_to_username = dict(zip(self.user_ids, self.usernames))
        # словарь для хранения since_id
        self.since_ids: Dict[str,str] = {uid: None for uid in self.user_ids}
        self.poll_interval = poll_interval

    async def stream_tweets(self) -> AsyncGenerator[Dict, None]:
        """
        Async-генератор новых твитов.
        Каждые poll_interval секунд опрашивает get_users_tweets
        для каждого user_id и выдаёт новые твиты по одному.
        """
        while True:
            for uid in self.user_ids:
                # синхронный вызов API оборачиваем в asyncio.to_thread
                resp = await asyncio.to_thread(
                    self.client.get_users_tweets,
                    uid,
                    since_id=self.since_ids[uid],
                    tweet_fields=["author_id","id","text"]
                )
                tweets = resp.data or []
                # если есть новые — сортируем по возрастанию ID, выдаём в правильном порядке
                tweets.sort(key=lambda t: t.id)
                for tweet in tweets:
                    self.since_ids[uid] = tweet.id
                    yield {
                        "id": tweet.id,
                        "text": tweet.text,
                        "author_username": self.id_to_username[uid]
                    }
            await asyncio.sleep(self.poll_interval)
