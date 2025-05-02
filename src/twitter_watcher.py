# src/twitter_watcher.py

import os
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, List

import tweepy
from tweepy.errors import TooManyRequests, TweepyException

class TwitterWatcher:
    """
    Асинхронный генератор новых твитов через Twitter API v2 с
    ручной обработкой rate-limit’а.
    """

    def __init__(
        self,
        bearer_token: str = None,
        poll_interval: int = 60,
        max_results: int = 5,
    ):
        token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        if not token:
            raise ValueError("Не задан TWITTER_BEARER_TOKEN")
        # Отключаем автоматический sleep в Tweepy, чтобы не блокировать asyncio
        self.client = tweepy.Client(
            bearer_token=token,
            wait_on_rate_limit=False
        )

        raw = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames: List[str] = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Нужно указать WATCH_TWITTER_USERS в .env")

        # Получаем ID пользователей единожды
        self.user_ids: Dict[str, int] = {}
        for username in self.usernames:
            user = self.client.get_user(username=username)
            if not user.data:
                raise RuntimeError(f"Не удалось найти @{username}")
            self.user_ids[username] = user.data.id

        self.poll_interval = poll_interval
        self.max_results   = max_results
        # для каждого username — последний seen tweet ID
        self.since_id: Dict[str, int] = {u: None for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд опрашиваем get_users_tweets,
        обрабатываем TooManyRequests через asyncio.sleep и
        не падаем на rate-limit.
        """
        while True:
            for username, uid in self.user_ids.items():
                last_id = self.since_id[username]
                try:
                    resp = self.client.get_users_tweets(
                        id=uid,
                        since_id=last_id,
                        max_results=self.max_results,
                        tweet_fields=["created_at", "text"],
                    )
                    tweets = resp.data or []
                except TooManyRequests as e:
                    # вытаскиваем время сброса из заголовка, если есть
                    reset = e.response.headers.get("x-rate-limit-reset")
                    if reset:
                        wait = int(reset) - int(time.time()) + 5
                    else:
                        wait = self.poll_interval
                    logging.warning(f"Rate limit for @{username}, sleeping {wait}s")
                    await asyncio.sleep(wait)
                    continue
                except TweepyException as e:
                    logging.error(f"Tweepy error for @{username}: {e}")
                    continue

                # сортируем и отдаем в хронологическом порядке
                tweets_sorted = sorted(tweets, key=lambda t: t.id)
                for tweet in tweets_sorted:
                    self.since_id[username] = tweet.id
                    yield {
                        "id":               tweet.id,
                        "text":             tweet.text,
                        "author_username":  username,
                    }

            await asyncio.sleep(self.poll_interval)
