# src/twitter_watcher.py

import os
import time
import logging
import asyncio
from typing import AsyncGenerator, Dict

import tweepy
from tweepy import OAuth1UserHandler, API

class TwitterWatcher:
    """
    Async-генератор твитов нескольких пользователей через v1.1 user_timeline,
    обходя ограничения бесплатного v2.
    """

    def __init__(self, poll_interval: int = 60):
        # 1) OAuth1 авторизация (v1.1)
        auth = OAuth1UserHandler(
            os.getenv("TWITTER_API_KEY"),
            os.getenv("TWITTER_API_SECRET"),
            os.getenv("TWITTER_ACCESS_TOKEN"),
            os.getenv("TWITTER_ACCESS_SECRET"),
        )
        self.api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

        # 2) Список имён и их ID (screen_name и numeric ID)
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        raw_ids   = os.getenv("WATCH_TWITTER_USER_IDS", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        self.user_ids   = [i.strip() for i in raw_ids.split(",")   if i.strip()]

        if len(self.usernames) != len(self.user_ids) or not self.user_ids:
            raise ValueError("WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS должны совпадать и быть непустыми")

        # 3) since_id для каждого пользователя — чтобы не получать старые твиты
        self.since_ids: Dict[str,int] = {uid: None for uid in self.user_ids}

        # 4) Интервал между опросами
        self.poll_interval = poll_interval

    async def stream_tweets(self) -> AsyncGenerator[Dict, None]:
        """
        Каждые poll_interval секунд опрашивает /1.1/statuses/user_timeline
        для каждого screen_name, выдаёт только новые твиты.
        """
        while True:
            for uname, uid in zip(self.usernames, self.user_ids):
                try:
                    # синхронный вызов в thread pool
                    timeline = await asyncio.to_thread(
                        self.api.user_timeline,
                        screen_name=uname,
                        since_id=self.since_ids[uid],
                        tweet_mode="extended",
                        count=10
                    )
                except Exception as e:
                    logging.warning(f"Ошибка user_timeline для {uname}: {e}")
                    continue

                # reverse, чтобы выдавать от старых к свежим
                for status in reversed(timeline):
                    # full_text для твитов длиной >280 символов
                    text = getattr(status, "full_text", status.text)
                    self.since_ids[uid] = max(self.since_ids[uid] or 0, status.id)
                    yield {
                        "id": status.id,
                        "text": text,
                        "author_username": uname
                    }

            # ждём прежде чем опрашивать всех снова
            await asyncio.sleep(self.poll_interval)
