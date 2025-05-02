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

async def handle_tweet(tweet, summarizer, img_gen, pump, notifier):
    text = tweet["text"]
    url  = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
    logging.info(f"Новый твит: {url}")

    summary   = await summarizer.summarize(text)
    image_url = (await img_gen.generate(summary))[0]
    logging.info(f"Картинка: {image_url}")

    ticker = generate_ticker(summary)
    name   = summary.title()

    metadata = {
        "name":         name,
        "symbol":       ticker,
        "description":  summary,
        "external_url": url,
        "image":        image_url
    }
    b64 = base64.b64encode(json.dumps(metadata).encode()).decode()
    uri = f"data:application/json;base64,{b64}"

    result = await pump.create_token(name=name, symbol=ticker, uri=uri)
    logging.info(f"Создан токен: {result}")

    notifier.notify(
        text=(
            f"✅ Токен *{name}* (`${ticker}`)\n"
            f"[Твит]({url}) • [Картинка]({image_url})\n"
            f"Tx: https://solscan.io/tx/{result['tx']}"
        ),
        parse_mode="Markdown"
    )

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()

    # Настройка
    usernames = os.getenv("WATCH_TWITTER_USERS", "").split(",")
    watcher   = TwitterWatcher(os.getenv("TWITTER_BEARER_TOKEN"), usernames)
    summarizer= AISummarizer(os.getenv("OPENAI_API_KEY"))
    img_gen   = AIImageGenerator(os.getenv("OPENAI_API_KEY"))
    pump      = PumpClient()
    chat_ids  = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS","").split(",") if cid.strip()]
    notifier  = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), chat_ids)

    # Stream loop
    async for tweet in watcher.stream_tweets():
        asyncio.create_task(handle_tweet(tweet, summarizer, img_gen, pump, notifier))

if __name__ == "__main__":
    asyncio.run(main())



if __name__ == "__main__":
    asyncio.run(main())

