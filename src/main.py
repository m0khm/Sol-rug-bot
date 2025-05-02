
# src/main.py

import os
import certifi

# Указываем Python SSL и requests использовать корневые сертификаты из certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import asyncio
import logging
import json
import base64

from dotenv import load_dotenv
from twitter_watcher import TwitterWatcher   # snscrape-based implementation
from ai_summarizer import AISummarizer
from ai_image_generator import AIImageGenerator
from ticker_generator import generate_ticker
from pump_client import PumpClient
from telegram_notifier import TelegramNotifier

async def handle_tweet(tweet, summarizer, img_gen, pump, notifier):
    text = tweet["text"]
    url  = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
    logging.info(f"Новый твит: {url}")

    # 1) Сжимаем текст
    summary = await summarizer.summarize(text)

    # 2) Генерируем картинку
    image_url = (await img_gen.generate(summary))[0]
    logging.info(f"Сгенерирована картинка: {image_url}")

    # 3) Генерируем тикер и имя токена
    ticker = generate_ticker(summary)
    name   = summary.title()

    # 4) Формируем метаданные и кодируем их в data URI
    metadata = {
        "name":         name,
        "symbol":       ticker,
        "description":  summary,
        "external_url": url,
        "image":        image_url
    }
    md_b64 = base64.b64encode(json.dumps(metadata).encode()).decode()
    metadata_uri = f"data:application/json;base64,{md_b64}"

    # 5) Создаём токен on-chain через Pump.fun
    result = await pump.create_token(name=name, symbol=ticker, uri=metadata_uri)
    logging.info(f"Токен создан: {result}")

    # 6) Уведомляем в Telegram
    notifier.notify(
        text=(
            f"✅ Создан токен *{name}* (`${ticker}`)\n"
            f"[▶️ Твит]({url})  [🖼️ Картинка]({image_url})\n"
            f"Tx: https://solscan.io/tx/{result['tx']}"
        ),
        parse_mode="Markdown"
    )

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    logging.getLogger("snscrape").setLevel(logging.INFO)
    load_dotenv()

    # Интервал опроса твитов через snscrape (в секундах)
    poll_interval = int(os.getenv("TWEET_POLL_INTERVAL", "60"))

    # Инициализируем watcher (snscrape-based)
    watcher    = TwitterWatcher(poll_interval=poll_interval)

    summarizer = AISummarizer(os.getenv("OPENAI_API_KEY"))
    img_gen    = AIImageGenerator(os.getenv("OPENAI_API_KEY"))
    pump       = PumpClient()
    chat_ids   = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if cid.strip()]
    notifier   = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), chat_ids)

    # Асинхронно обрабатываем новые твиты
    async for tweet in watcher.stream_tweets():
        asyncio.create_task(handle_tweet(tweet, summarizer, img_gen, pump, notifier))

if __name__ == "__main__":
    asyncio.run(main())
