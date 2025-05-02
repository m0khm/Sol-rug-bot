# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator
import feedparser

class TwitterWatcher:
    """
    Async-генератор новых твитов через Nitter-RSS.
    Каждые poll_interval секунд дергаем RSS и отдаём новые entry.
    """

    def __init__(self, poll_interval: int = 60):
        raw = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Задайте WATCH_TWITTER_USERS в .env")

        self.poll_interval = poll_interval
        # для каждого юзера храним последний обработанный guid/id
        self.seen_ids = {u: set() for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        while True:
            for username in self.usernames:
                try:
                    new_items = await asyncio.to_thread(self._fetch_rss, username)
                except Exception as e:
                    logging.error(f"RSS error for {username}: {e}")
                    continue

                for entry in new_items:
                    yield {
                        "id":               entry.id,       # например, URL поста
                        "text":             entry.title,    # заголовок — текст твита
                        "author_username":  username
                    }

            await asyncio.sleep(self.poll_interval)

    def _fetch_rss(self, username: str):
        url = f"https://nitter.net/{username}/rss"
        feed = feedparser.parse(url)
        if feed.bozo:
            raise RuntimeError(f"Invalid RSS for {username}: {feed.bozo_exception}")

        new_entries = []
        for entry in feed.entries:
            if entry.id not in self.seen_ids[username]:
                new_entries.append(entry)
                self.seen_ids[username].add(entry.id)

        # Опционально: сортировать по дате, если нужно
        new_entries.sort(key=lambda e: e.published_parsed)
        return new_entries
