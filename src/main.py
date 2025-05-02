# src/main.py

import os
import asyncio
import logging
import json
import base64

from dotenv import load_dotenv
from twitter_watcher import TwitterWatcher
from ai_summarizer import AISummarizer
from ai_image_generator import AIImageGenerator
from ticker_generator import generate_ticker
from pump_client import PumpClient
from telegram_notifier import TelegramNotifier


async def handle_tweet(tweet: dict, summarizer, img_gen, pump, notifier):
    text = tweet["text"]
    url = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
    logging.info(f"Новый твит: {url}")

    # 1) сжимаем текст
    summary = await summarizer.summarize(text)
    # 2) генерируем картинку
    image_url = (await img_gen.generate(summary))[0]
    logging.info("Сгенерирована картинка: %s", image_url)

    # 3) генерируем тикер и имя токена
    ticker = generate_ticker(summary)
    name = summary.title()

    # 4) метаданные в data: URI
    metadata = {
        "name": name,
        "symbol": ticker,
        "description": summary,
        "external_url": url,
        "image": image_url,
    }
    md_b64 = base64.b64encode(json.dumps(metadata).encode()).decode()
    metadata_uri = f"data:application/json;base64,{md_b64}"

    # 5) создаём токен
    result = await pump.create_token(name=name, symbol=ticker, uri=metadata_uri)
    logging.info("Создан токен: %s", result)

    # 6) оповещаем в Telegram
    notifier.notify(
        text=(
            f"✅ Создан токен *{name}* (`${ticker}`)\n"
            f"[Твит]({url}) • [Картинка]({image_url})\n"
            f"Tx: https://solscan.io/tx/{result['tx']}"
        ),
        parse_mode="Markdown",
    )


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    load_dotenv()

    # компоненты
    watcher = TwitterWatcher(
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        username=os.getenv("WATCH_TWITTER_USER"),
    )
    summarizer = AISummarizer(os.getenv("OPENAI_API_KEY"))
    img_gen = AIImageGenerator(os.getenv("OPENAI_API_KEY"))
    pump = PumpClient()

    chat_ids = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if cid.strip()]
    notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), chat_ids)

    # основной цикл
    async for tweet in watcher.stream_tweets():
        # обрабатываем каждый твит независимо,
        # чтобы не блокировать получение следующих
        asyncio.create_task(handle_tweet(tweet, summarizer, img_gen, pump, notifier))


if __name__ == "__main__":
    asyncio.run(main())

