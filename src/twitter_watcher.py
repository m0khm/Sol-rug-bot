# src/twitter_watcher.py

# ── MONKEY-PATCH для Python 3.12: FileFinder.find_module → FileFinder.find_spec
import importlib.machinery
if not hasattr(importlib.machinery.FileFinder, "find_module"):
    importlib.machinery.FileFinder.find_module = importlib.machinery.FileFinder.find_spec
# ── конец патча

import os
import time
import logging
import asyncio
from typing import AsyncGenerator, Dict

import snscrape.modules.twitter as sntwitter

class TwitterWatcher:
    """
    Async-генератор твитов нескольких пользователей через snscrape,
    без официального API, c патчем для Python 3.12.
    """

    def __init__(self, poll_interval: int = 60, max_fetch: int = 20):
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Задайте WATCH_TWITTER_USERS в .env")

        self.poll_interval = poll_interval
        self.max_fetch     = max_fetch
        self.since_id: Dict[str,int] = {u: 0 for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд сканит через snscrape TwitterUserScraper
        и отдаёт новые твиты в хронологическом порядке.
        """
        while True:
            for username in self.usernames:
                tweets = await asyncio.to_thread(self._fetch_new, username)
                for t in tweets:
                    yield {
                        "id":               t.id,
                        "text":             t.content,
                        "author_username":  username
                    }
            await asyncio.sleep(self.poll_interval)

    def _fetch_new(self, username: str):
        scraper = sntwitter.TwitterUserScraper(username)
        new_items = []
        for i, tweet in enumerate(scraper.get_items()):
            if i >= self.max_fetch:
                break
            if tweet.id <= self.since_id[username]:
                continue
            new_items.append(tweet)

        if not new_items:
            return []

        max_id = max(t.id for t in new_items)
        self.since_id[username] = max_id
        return sorted(new_items, key=lambda t: t.id)
