# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator, Dict
import snscrape.modules.twitter as sntwitter
from snscrape.base import ScraperException

class TwitterWatcher:
    """
    Async-генератор твитов нескольких пользователей через snscrape,
    с fallback на SearchScraper вместо UserScraper.
    """

    def __init__(self, poll_interval: int = 60, max_fetch: int = 20):
        raw = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Задайте WATCH_TWITTER_USERS в .env")

        self.poll_interval = poll_interval
        self.max_fetch     = max_fetch
        # для каждого username храним последний обработанный ID
        self.since_id: Dict[str,int] = {u: 0 for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд пытаемся достать новые твиты через SearchScraper.
        При ошибке — логируем и переходим к следующему циклу.
        """
        while True:
            for username in self.usernames:
                try:
                    tweets = await asyncio.to_thread(self._fetch_new, username)
                except ScraperException as e:
                    logging.error(f"snscrape error for {username}: {e}")
                    continue

                for t in tweets:
                    yield {
                        "id":               t.id,
                        "text":             t.content,
                        "author_username":  username
                    }

            await asyncio.sleep(self.poll_interval)

    def _fetch_new(self, username: str):
        """
        Достаём твиты через TwitterSearchScraper("from:username"),
        фильтруем по since_id, сортируем от старых к новым.
        """
        query = f"from:{username}"
        scraper = sntwitter.TwitterSearchScraper(query)
        new_items = []

        for i, tweet in enumerate(scraper.get_items()):
            if i >= self.max_fetch:
                break
            if tweet.id <= self.since_id[username]:
                continue
            new_items.append(tweet)

        if not new_items:
            return []

        # обновляем since_id
        self.since_id[username] = max(t.id for t in new_items)
        # возвращаем в хронологическом порядке
        return sorted(new_items, key=lambda t: t.id)
