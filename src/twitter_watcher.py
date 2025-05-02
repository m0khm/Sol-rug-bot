# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator, Dict
import tweepy
from tweepy.errors import TooManyRequests

class TwitterWatcher:
    """
    Async-генератор новых твитов от нескольких пользователей,
    объединяя их в один запрос search_recent_tweets и
    корректно обрабатывая rate limits.
    """

    def __init__(
        self,
        bearer_token: str,
        poll_interval: int = 60,
        max_results: int = 100
    ):
        self.client = tweepy.Client(bearer_token=bearer_token)

        # 1) Читаем из .env два списка: WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        raw_ids   = os.getenv("WATCH_TWITTER_USER_IDS", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        self.user_ids   = [i.strip() for i in raw_ids.split(",")   if i.strip()]

        if not self.user_ids or len(self.user_ids) != len(self.usernames):
            raise ValueError(
                "WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS должны быть заданы и одинаковой длины"
            )

        # 2) Создаём общую строку запроса и маппинг id→username
        self.query = " OR ".join(f"from:{uid}" for uid in self.user_ids)
        self.id_to_username: Dict[str,str] = dict(zip(self.user_ids, self.usernames))

        # 3) Параметры poll и max_results
        self.poll_interval = poll_interval
        self.max_results   = max_results

        # 4) Храним since_id для всего запроса
        self.since_id: str | None = None

    async def stream_tweets(self) -> AsyncGenerator[Dict, None]:
        """
        Каждые poll_interval секунд делает один запрос к search_recent_tweets,
        отдаёт новые твиты по одному в хронологическом порядке.
        При rate-limit ждёт до x-rate-limit-reset.
        """
        while True:
            try:
                # Делаем синхронный вызов API в pool потоков
                resp = await asyncio.to_thread(
                    self.client.search_recent_tweets,
                    query=self.query,
                    since_id=self.since_id,
                    tweet_fields=["author_id", "id", "text"],
                    max_results=self.max_results
                )
            except TooManyRequests as e:
                import time
                # UNIX timestamp сброса лимита или fallback на now+poll_interval
                reset_ts = int(e.response.headers.get(
                    "x-rate-limit-reset", time.time() + self.poll_interval
                ))
                # время ожидания (мин. poll_interval)
                wait = max(reset_ts - time.time(), self.poll_interval)
                logging.warning(
                    f"Rate limit hit, sleeping {wait:.0f}s until "
                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_ts))}"
                )
                await asyncio.sleep(wait)
                continue

            tweets = resp.data or []
            # Сортируем по возрастанию ID
            tweets.sort(key=lambda t: t.id)

            for t in tweets:
                # Обновляем since_id
                if self.since_id is None or t.id > int(self.since_id):
                    self.since_id = str(t.id)
                yield {
                    "id":               t.id,
                    "text":             t.text,
                    "author_username":  self.id_to_username.get(str(t.author_id), str(t.author_id))
                }

            # Ждём перед следующим опросом
            await asyncio.sleep(self.poll_interval)
