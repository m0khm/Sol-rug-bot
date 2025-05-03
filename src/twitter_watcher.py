# src/twitter_watcher.py

import asyncio
import logging
import importlib
from importlib.machinery import FileFinder

# Патчим FileFinder для snscrape (Python 3.12 убрал find_module)
def _find_module(self, fullname, path=None):
    spec = self.find_spec(fullname, path)
    return spec.loader if spec else None

# Если у FileFinder нет find_module — добавляем
if not hasattr(FileFinder, 'find_module'):
    FileFinder.find_module = _find_module

from snscrape.modules.twitter import TwitterSearchScraper

logger = logging.getLogger(__name__)

class TwitterWatcher:
    """
    Асинхронный «наблюдатель» твитов указанного пользователя
    через snscrape (без tweepy).
    """
    def __init__(self, username: str, poll_interval: int = 30):
        """
        :param username: никнейм без "@"
        :param poll_interval: интервал опроса в секундах
        """
        self.username = username
        self.poll_interval = poll_interval
        self.since_id = None

    async def watch(self):
        """
        Async-генератор новых твитов.
        """
        query = f"from:{self.username}"
        scraper = TwitterSearchScraper(query)

        while True:
            try:
                # в отдельном потоке приводим итератор к списку
                tweets = await asyncio.to_thread(lambda: list(scraper.get_items()))
                # фильтруем только новые
                new = [t for t in tweets if self.since_id is None or t.id > self.since_id]

                if new:
                    # запоминаем самый свежий id
                    self.since_id = max(t.id for t in new)
                    # отдаём по одному в хронологическом порядке
                    for t in sorted(new, key=lambda x: x.date):
                        yield t

            except Exception as e:
                logger.exception("Ошибка сбора твитов %s: %s", self.username, e)

            await asyncio.sleep(self.poll_interval)
