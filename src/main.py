#!/usr/bin/env python3
# src/main.py

import os
import asyncio
import logging
from dotenv import load_dotenv

from twitter_watcher import TwitterWatcher
from ai_summarizer import AISummarizer
from ai_image_generator import AIImageGenerator
from ticker_generator import TickerGenerator
from pump_client import PumpClient
from telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # 1) Загружаем .env
    load_dotenv()

    # 2) Читаем имя пользователя из env
    twitter_username = os.getenv('TWITTER_USERNAME')
    if not twitter_username:
        logger.error("Переменная окружения TWITTER_USERNAME не задана")
        return

    # 3) Интервал опроса
    poll_interval = int(os.getenv('TWEET_POLL_INTERVAL', '60'))

    # 4) OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        logger.error("Переменная окружения OPENAI_API_KEY не задана")
        return

    # 5) Solana
    solana_rpc    = os.getenv('SOLANA_RPC_ENDPOINT')
    secret_key    = os.getenv('SOLANA_SECRET_KEY')
    # Pump.fun program ID по-хорошему тоже в env, но у вас, видимо, он уже прописан в коде

    # 6) Telegram
    telegram_token   = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chats   = os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
    if not telegram_token or not telegram_chats:
        logger.error("Telegram не сконфигурирован (BOT_TOKEN/CHAT_IDS)")
        return

    # === Инициализация компонентов ===

    # Тут — главное изменение: передаём username как позиционный аргумент
    watcher    = TwitterWatcher(username=twitter_username, poll_interval=poll_interval)
    summarizer = AISummarizer(api_key=openai_key)
    img_gen    = AIImageGenerator(api_key=openai_key)
    ticker_gen = TickerGenerator()
    pump       = PumpClient(rpc_endpoint=solana_rpc, payer_keypair_path=secret_key)
    notifier   = TelegramNotifier(token=telegram_token, chat_ids=telegram_chats)

    # === Основной loop ===
    async for tweet in watcher.watch():
        logger.info(f"Новый твит @{twitter_username}: {tweet.id}")
        summary   = await summarizer.summarize(tweet.content)
        img_url   = await img_gen.generate_image(summary)
        ticker    = ticker_gen.generate()
        mint_addr = await pump.mint_token(
            name=ticker, symbol=ticker, uri=img_url,
            metadata={"description": summary, "tweet_url": tweet.url}
        )
        await notifier.send_message(
            text=f"Minted *{ticker}* for [{tweet.id}]({tweet.url})\n\n{summary}",
            token_address=mint_addr,
            image_url=img_url
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота")
