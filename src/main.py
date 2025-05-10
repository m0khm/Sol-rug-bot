#!/usr/bin/env python3
# src/main.py

import os
import asyncio
import logging
import uuid
import requests

from dotenv import load_dotenv

from twitter_watcher import TwitterWatcher
from ai_summarizer import AISummarizer
from ai_image_generator import AIImageGenerator
from ticker_generator import TickerGenerator
from telegram_notifier import TelegramNotifier

from selenium_pump import PumpSeleniumBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()

    # --- читаем env ---
    twitter_username = os.getenv("TWITTER_USERNAME")
    if not twitter_username:
        raise RuntimeError("TWITTER_USERNAME не задан")
    poll_interval = int(os.getenv("TWEET_POLL_INTERVAL", "60"))

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY не задан")

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chats = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    if not tg_token or not tg_chats:
        raise RuntimeError("Telegram не сконфигурирован")

    chrome_profile = os.getenv("CHROME_PROFILE_DIR")
    if not chrome_profile:
        raise RuntimeError("CHROME_PROFILE_DIR не задан")
    chromedriver = os.getenv("CHROMEDRIVER_PATH", "chromedriver")
    headless = os.getenv("PUMP_HEADLESS", "false").lower() == "true"

    initial_price = float(os.getenv("INITIAL_PRICE_USD", "0.01"))
    fee_pct   = float(os.getenv("BONDING_FEE_PCT", "1.0"))
    exponent  = float(os.getenv("CURVE_EXPONENT", "1.0"))
    reserve   = float(os.getenv("INITIAL_RESERVE_SOL", "0.0"))

    # --- инициализация ---
    watcher   = TwitterWatcher(username=twitter_username, poll_interval=poll_interval)
    summarizer= AISummarizer(api_key=openai_key)
    imggen    = AIImageGenerator(api_key=openai_key)
    tickergen = TickerGenerator()
    notifier  = TelegramNotifier(token=tg_token, chat_ids=tg_chats)

    pump = PumpSeleniumBot(
        profile_dir=chrome_profile,
        driver_path=chromedriver,
        headless=headless
    )
    pump.connect_wallet()

    # убедимся, что папка для картинок есть
    os.makedirs("images", exist_ok=True)

    async for tweet in watcher.watch():
        logger.info(f"Новый твит @{twitter_username}: {tweet.id}")

        # 1) Summary
        summary = await summarizer.summarize(tweet.content)

        # 2) Иллюстрация (OpenAI возвращает URL)
        image_url = await imggen.generate_image(summary)

        # 3) Скачиваем картинку локально
        ext = os.path.splitext(image_url.split("?")[0])[-1] or ".png"
        local_path = f"images/{uuid.uuid4()}{ext}"
        resp = requests.get(image_url)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)

        # 4) Тикер
        ticker = tickergen.generate()

        # 5) Создаём токен через Selenium
        pump.create_token(
            name=ticker,
            ticker=ticker,
            price_usd=initial_price,
            description=summary,
            image_path=local_path,
            fee_pct=fee_pct,
            curve_exponent=exponent,
            initial_reserve_sol=reserve
        )

        # 6) Уведомляем
        await notifier.send_message(
            text=(
                f"Создан токен *{ticker}* для твита "
                f"[{tweet.id}](https://twitter.com/{twitter_username}/status/{tweet.id})\n\n"
                f"{summary}"
            ),
            token_address=None,
            image_url=image_url
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Выход по Ctrl+C")
