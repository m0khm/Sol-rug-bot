# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator
import snscrape.modules.twitter as sntwitter
from snscrape.base import ScraperException

class TwitterWatcher:
    """
    Async-генератор твитов нескольких пользователей через snscrape.
    При любых ошибках скрейпинга — логируем и ждем следующего poll_interval.
    """

    def __init__(self, poll_interval: int = 60, max_fetch: int = 20):
        raw = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Задайте WATCH_TWITTER_USERS в .env")

        self.poll_interval = poll_interval
        self.max_fetch     = max_fetch
        # для каждого username хранится последний обработанный ID
        self.since_id = {u: 0 for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд сканим твиты пользователя,
        но если snscrape упал — просто пропускаем и ждём следующего цикла.
        """
        while True:
            for username in self.usernames:
                try:
                    tweets = await asyncio.to_thread(self._fetch_new, username)
                except ScraperException as e:
                    logging.error(f"snscrape error for {username}: {e}")
                    # не падаем, переходим к следующему
                    continue

                # отдаём новые твиты в порядке старше→свежие
                for t in tweets:
                    yield {
                        "id":               t.id,
                        "text":             t.content,
                        "author_username":  username
                    }

            await asyncio.sleep(self.poll_interval)

    def _fetch_new(self, username: str):
        """
        Возвращает список новых tweet-объектов, сортированных по id.
        """
        scraper = sntwitter.TwitterUserScraper(username)
        items = []
        for i, tweet in enumerate(scraper.get_items()):
            if i >= self.max_fetch:
                break
            if tweet.id <= self.since_id[username]:
                continue
            items.append(tweet)

        if not items:
            return []

        # обновляем since_id до максимального
        self.since_id[username] = max(t.id for t in items)
        # возвращаем по возрастанию id
        return sorted(items, key=lambda t: t.id)
