# src/twitter_watcher.py

import os
import asyncio
import logging
from typing import AsyncGenerator, List
import feedparser

class TwitterWatcher:
    """
    Асинхронный генератор новых твитов через twitrss.me.
    Каждые poll_interval секунд дергаем RSS и отдаём новые entry.
    """

    def __init__(self, poll_interval: int = 60):
        raw = os.getenv("WATCH_TWITTER_USERS", "")
        self.usernames: List[str] = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.usernames:
            raise ValueError("Задайте WATCH_TWITTER_USERS в .env")

        self.poll_interval = poll_interval
        # для каждого username храним уже виденные GUID
        self.seen_ids = {u: set() for u in self.usernames}

    async def stream_tweets(self) -> AsyncGenerator[dict, None]:
        """
        Каждые poll_interval секунд дергаем RSS twitrss.me
        и отдаём новые записи.
        """
        while True:
            for username in self.usernames:
                try:
                    new_entries = await asyncio.to_thread(self._fetch_rss, username)
                except Exception as e:
                    logging.error(f"RSS error for {username}: {e}")
                    continue

                for entry in new_entries:
                    yield {
                        "id":               getattr(entry, "id", entry.link),
                        "text":             entry.title,
                        "author_username":  username
                    }

            await asyncio.sleep(self.poll_interval)

    def _fetch_rss(self, username: str):
        """
        Возвращает список feedparser.Entry новых твитов для username.
        Если feed.bozo==True, но есть записи — просто логируем и продолжаем.
        Если записей нет — кидаем ошибку.
        """
        url = f"https://twitrss.me/twitter_user_to_rss/?user={username}"
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "Mozilla/5.0"}
        )

        if feed.bozo:
            logging.warning(f"[RSS bozo] for {username}: {feed.bozo_exception}")

        entries = feed.entries or []
        if not entries:
            # действительно пусто — это уже критично
            raise RuntimeError(f"Empty RSS for {username}")

        new_entries = []
        for entry in entries:
            entry_id = getattr(entry, "id", entry.link)
            if entry_id in self.seen_ids[username]:
                continue
            self.seen_ids[username].add(entry_id)
            new_entries.append(entry)

        new_entries.sort(key=lambda e: e.published_parsed)
        logging.info(f"[RSS fetch for {username}]: {len(new_entries)} new")
        return new_entries
