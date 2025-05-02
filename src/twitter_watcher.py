# src/twitter_watcher.py

import os
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict

import snscrape.modules.twitter as sntwitter

class TwitterWatcher:
    """
    Async-генератор твитов нескольких пользователей через snscrape,
    без официального Twitter API.
    """

    def __init__(self, poll_interval: int = 60, max_fetch: int = 20):
        # Список юзернеймов
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Задайте WATCH_TWITTER_USERS в .env")

        # Интервал опроса и макс. твитов за цикл
        self.poll_interval = poll_interval
        self.max_fetch     = max_fetch

        # Храним since_id (последний обработанный tweet.id) на пользователя
        self.since_id: Dict[str,int] = {u: 0 for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд сканит через snscrape TwitterUserScraper
        и отдаёт новые твиты в хронологическом порядке.
        """
        while True:
            for username in self.usernames:
                # вызов snscrape в thread pool
                tweets = await asyncio.to_thread(self._fetch_new, username)
                for t in tweets:
                    yield {
                        "id":               t.id,
                        "text":             t.content,
                        "author_username":  username
                    }
            await asyncio.sleep(self.poll_interval)

    def _fetch_new(self, username: str):
        """
        Возвращает упорядоченный по времени список новых твитов пользователя.
        """
        scraper = sntwitter.TwitterUserScraper(username)
        new_items = []
        for i, tweet in enumerate(scraper.get_items()):
            if i >= self.max_fetch:
                break
            # snscrape Tweet object имеет атрибут id (int) и content (text)
            if tweet.id <= self.since_id[username]:
                continue
            new_items.append(tweet)
        if not new_items:
            return []
        # Установим новый since_id по самому большому ID
        max_id = max(t.id for t in new_items)
        self.since_id[username] = max_id
        # Вернём в порядке от старых к новым
        return sorted(new_items, key=lambda t: t.id)
