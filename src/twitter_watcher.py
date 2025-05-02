# src/twitter_watcher.py

import os
import logging
import tweepy
from typing import List

class TwitterWatcher:
    """
    Стримит твиты сразу нескольких пользователей через v2 Filtered Stream,
    минимизируя число API-вызовов:
      - user_ids читаются из окружения, без get_user
      - правило создаётся только один раз, если его ещё нет
    """

    def __init__(self, bearer_token: str):
        self.client = tweepy.Client(bearer_token=bearer_token)

        # Читаем из .env два списка: юзернеймы и их ID
        raw_users = os.getenv("WATCH_TWITTER_USERS", "")
        raw_ids   = os.getenv("WATCH_TWITTER_USER_IDS", "")
        self.usernames: List[str] = [u.strip() for u in raw_users.split(",") if u.strip()]
        self.user_ids:   List[str] = [i.strip() for i in raw_ids.split(",")   if i.strip()]

        if not self.usernames or not self.user_ids:
            raise ValueError("Не заданы WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS в .env")

        if len(self.usernames) != len(self.user_ids):
            raise ValueError("Кол-во WATCH_TWITTER_USERS и WATCH_TWITTER_USER_IDS должно совпадать")

        # Словарь для обратного маппинга author_id → username
        self.id_to_username = dict(zip(self.user_ids, self.usernames))

    def stream_tweets(self):
        """
        Генератор новых твитов.
        Устанавливает правило «from:id1 OR from:id2 OR …» один раз
        и затем бесконечно читает из потока.
        """
        stream = tweepy.StreamingClient(
            bearer_token=self.client.bearer_token,
            wait_on_rate_limit=True
        )

        # Получаем существующие правила
        existing = stream.get_rules().data or []

        if not existing:
            rule_value = " OR ".join(f"from:{uid}" for uid in self.user_ids)
            stream.add_rules(tweepy.StreamRule(value=rule_value))
            logging.info(f"Добавлено правило Filtered Stream: {rule_value}")
        else:
            # Если правило уже есть, выводим его для отладки
            vals = [r.value for r in existing]
            logging.info(f"Существующие правила Filtered Stream: {vals}")

        # Бесконечный стрим
        for tweet in stream.filter(tweet_fields=["author_id", "id", "text"]):
            yield {
                "id": tweet.id,
                "text": tweet.text,
                "author_username": self.id_to_username.get(tweet.author_id, str(tweet.author_id))
            }
