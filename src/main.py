# src/main.py

import os
import asyncio
import logging
import json
import base64
import certifi

# Ensure Python SSL uses certifi certificates
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from dotenv import load_dotenv
from twitter_watcher import TwitterWatcher  # snscrape-based implementation
from ai_summarizer import AISummarizer
from ai_image_generator import AIImageGenerator
from ticker_generator import generate_ticker
from pump_client import PumpClient
from telegram_notifier import TelegramNotifier

async def handle_tweet(tweet, summarizer, img_gen, pump, notifier):
    text = tweet["text"]
    url = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
    logging.info(f"Новый твит: {url}")

    # 1) Summarize text
    summary = await summarizer.summarize(text)

    # 2) Generate image
    image_url = (await img_gen.generate(summary))[0]
    logging.info(f"Сгенерирована картинка: {image_url}")

    # 3) Generate ticker and token name
    ticker = generate_ticker(summary)
    name = summary.title()

    # 4) Prepare metadata URI
    metadata = {
        "name": name,
        "symbol": ticker,
        "description": summary,
        "external_url": url,
        "image": image_url
    }
    md_b64 = base64.b64encode(json.dumps(metadata).encode()).decode()
    metadata_uri = f"data:application/json;base64,{md_b64}"

    # 5) Create token via Pump.fun
    result = await pump.create_token(name=name, symbol=ticker, uri=metadata_uri)
    logging.info(f"Токен создан: {result}")

    # 6) Notify via Telegram
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
    load_dotenv()

    # Poll interval for scraping tweets
    poll_interval = int(os.getenv("TWEET_POLL_INTERVAL", "60"))

    # Initialize components
    watcher = TwitterWatcher(poll_interval=poll_interval)
    summarizer = AISummarizer(os.getenv("OPENAI_API_KEY"))
    img_gen = AIImageGenerator(os.getenv("OPENAI_API_KEY"))
    pump = PumpClient()
    chat_ids = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if cid.strip()]
    notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), chat_ids)

    # Process tweets asynchronously
    async for tweet in watcher.stream_tweets():
        asyncio.create_task(handle_tweet(tweet, summarizer, img_gen, pump, notifier))

if __name__ == "__main__":
    asyncio.run(main())
