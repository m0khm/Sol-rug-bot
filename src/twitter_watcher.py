# src/twitter_watcher.py

import asyncio
import logging
from snscrape.modules.twitter import TwitterSearchScraper

logger = logging.getLogger(__name__)

class TwitterWatcher:
    """
    Асинхронный «наблюдатель» твитов указанного пользователя,
    реализованный на базе snscrape. При появлении новых твитов
    выдаёт их по одному в порядке хронологии.
    """
    def __init__(self, username: str, poll_interval: int = 30):
        """
        :param username: никнейм пользователя без "@"
        :param poll_interval: интервал опроса в секундах
        """
        self.username = username
        self.poll_interval = poll_interval
        self.since_id = None

    async def watch(self):
        """
        Async-генератор, выдающий новые твиты.
        Использует asyncio.to_thread для вызова синхронного get_items().
        """
        query = f"from:{self.username}"
        scraper = TwitterSearchScraper(query)

        while True:
            try:
                # в фоне получаем список твитов
                tweets = await asyncio.to_thread(lambda: list(scraper.get_items()))
                new = []
                for t in tweets:
                    if self.since_id is None or t.id > self.since_id:
                        new.append(t)

                if new:
                    # обновляем since_id на самый свежий
                    self.since_id = max(t.id for t in new)
                    # сортируем по дате появления и отдаем по одному
                    for t in sorted(new, key=lambda x: x.date):
                        yield t

            except Exception as e:
                logger.exception("Ошибка при сборе твитов %s: %s", self.username, e)

            # ждём перед следующим запросом
            await asyncio.sleep(self.poll_interval)
