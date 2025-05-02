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

async def main():
    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    # Настраиваем компоненты
    watcher = TwitterWatcher(
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        username=os.getenv("WATCH_TWITTER_USER")
    )
    summarizer = AISummarizer(api_key=os.getenv("OPENAI_API_KEY"))
    img_gen     = AIImageGenerator(api_key=os.getenv("OPENAI_API_KEY"))
    pump        = PumpClient()

    # Читаем несколько chat_id из ENV
    raw_ids = os.getenv("TELEGRAM_CHAT_IDS", "")
    chat_ids = [cid.strip() for cid in raw_ids.split(",") if cid.strip()]
    notifier = TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_ids=chat_ids
    )

    async for tweet in watcher.stream_tweets():
        text = tweet["text"]
        url  = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
        logging.info(f"Новый твит: {url}")

        # 1) Сжимаем текст
        summary = summarizer.summarize(text)

        # 2) Генерируем картинку
        image_urls = img_gen.generate_image(summary)
        image_url  = image_urls[0]
        logging.info(f"Сгенерирована картинка: {image_url}")

        # 3) Генерируем тикер и название
        ticker = generate_ticker(summary)
        name   = summary.title()

        # 4) Собираем метаданные в data URI
        metadata = {
            "name":         name,
            "symbol":       ticker,
            "description":  summary,
            "external_url": url,
            "image":        image_url
        }
        md_json = json.dumps(metadata)
        md_b64  = base64.b64encode(md_json.encode()).decode()
        metadata_uri = f"data:application/json;base64,{md_b64}"

        # 5) Создаём токен on-chain
        result = await pump.create_token(
            name=name,
            symbol=ticker,
            uri=metadata_uri
        )
        logging.info(f"Создано: {result}")

        # 6) Уведомляем в Telegram (включая картинку)
        notifier.notify(
            text=(
                f"✅ Создан токен *{name}* (`${ticker}`)\n"
                f"[▶️ Посмотреть твит]({url})\n"
                f"[🖼️ Картинка]({image_url})\n"
                f"Tx: https://solscan.io/tx/{result['tx']}"
            ),
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    asyncio.run(main())
