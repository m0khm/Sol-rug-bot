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
    # Загружаем переменные из .env
    load_dotenv()

    # Никнейм Twitter (без @)
    twitter_username = os.getenv('TWITTER_USERNAME')
    if not twitter_username:
        logger.error("Переменная окружения TWITTER_USERNAME не задана")
        return

    # Интервал опроса твитов (секунды)
    poll_interval = int(os.getenv('POLL_INTERVAL', '30'))

    # Ключ OpenAI
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        logger.error("Переменная окружения OPENAI_API_KEY не задана")
        return

    # Настройки Solana / Pump.fun
    solana_rpc = os.getenv('SOLANA_RPC_ENDPOINT')
    pump_program_id = os.getenv('PUMP_PROGRAM_ID')
    payer_keypair = os.getenv('PAYER_KEYPAIR_PATH')

    # Telegram
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    # Инициализируем все компоненты
    watcher = TwitterWatcher(username=twitter_username, poll_interval=poll_interval)
    summarizer = AISummarizer(api_key=openai_api_key)
    image_generator = AIImageGenerator(api_key=openai_api_key)
    ticker_gen = TickerGenerator()
    pump_client = PumpClient(
        rpc_endpoint=solana_rpc,
        program_id=pump_program_id,
        payer_keypair_path=payer_keypair
    )
    notifier = TelegramNotifier(token=telegram_token, chat_id=telegram_chat_id)

    # Основной цикл: ждём новых твитов, обрабатываем их
    async for tweet in watcher.watch():
        logger.info(f"Новый твит @{twitter_username}: {tweet.id}")

        # 1) Суммируем
        summary = await summarizer.summarize(tweet.content)

        # 2) Генерируем иллюстрацию
        image_url = await image_generator.generate_image(summary)

        # 3) Генерим тикер
        ticker = ticker_gen.generate()

        # 4) Минтим токен через Pump.fun
        mint_address = await pump_client.mint_token(
            name=ticker,
            symbol=ticker,
            uri=image_url,
            metadata={
                "description": summary,
                "tweet_url": f"https://twitter.com/{twitter_username}/status/{tweet.id}"
            }
        )

        # 5) Уведомляем в Telegram
        await notifier.send_message(
            text=(
                f"Minted token *{ticker}* for tweet [{tweet.id}]"
                f"(https://twitter.com/{twitter_username}/status/{tweet.id})\n\n"
                f"{summary}"
            ),
            token_address=mint_address,
            image_url=image_url
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота по SIGINT")
