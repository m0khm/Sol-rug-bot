# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator, Dict, List

import tweepy


class TwitterWatcher:
    """
    Асинхронный генератор новых твитов через Twitter API v2.
    """

    def __init__(
        self,
        bearer_token: str = None,
        poll_interval: int = 60,
        max_results: int = 5,
    ):
        # Читаем параметры
        token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        if not token:
            raise ValueError("Не задан TWITTER_BEARER_TOKEN")
        self.client = tweepy.Client(bearer_token=token, wait_on_rate_limit=True)

        raw = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames: List[str] = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Нужно указать хотя бы один WATCH_TWITTER_USERS")

        # Получаем ID пользователей
        self.user_ids: Dict[str, int] = {}
        for username in self.usernames:
            user = self.client.get_user(username=username)
            if not user.data:
                raise RuntimeError(f"Не удалось найти пользователя @{username}")
            self.user_ids[username] = user.data.id

        self.poll_interval = poll_interval
        self.max_results   = max_results
        # для каждого username храним последний seen tweet ID
        self.since_id: Dict[str, int] = {u: None for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд опрашиваем get_users_tweets
        и отдаём только новые твиты.
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
                except Exception as e:
                    logging.error(f"Error fetching tweets for @{username}: {e}")
                    continue

                # Сортируем по возрастанию ID (или created_at)
                tweets_sorted = sorted(tweets, key=lambda t: t.id)
                for tweet in tweets_sorted:
                    # обновляем since_id сразу, чтобы не дублировать
                    self.since_id[username] = tweet.id
                    yield {
                        "id":               tweet.id,
                        "text":             tweet.text,
                        "author_username":  username,
                    }

            await asyncio.sleep(self.poll_interval)
