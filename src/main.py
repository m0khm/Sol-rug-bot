import os, asyncio, logging, json, base64
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

    watcher = TwitterWatcher(
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        username=os.getenv("WATCH_TWITTER_USER")
    )
    summarizer = AISummarizer(api_key=os.getenv("OPENAI_API_KEY"))
    img_gen     = AIImageGenerator(api_key=os.getenv("OPENAI_API_KEY"))
    pump        = PumpClient()
    notifier    = TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )

    async for tweet in watcher.stream_tweets():
        text = tweet["text"]
        url  = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
        logging.info(f"Новый твит: {url}")

        # 1) Сжимаем текст
        summary = summarizer.summarize(text)                       # => "very dangerous dog"

        # 2) Генерируем картинку
        image_urls = img_gen.generate_image(summary, n=1, size="512x512")
        image_url  = image_urls[0]
        logging.info(f"Сгенерирована картинка: {image_url}")

        # 3) Генерим тикер и название
        ticker = generate_ticker(summary)                         # => "VDD"
        name   = summary.title()                                  # => "Very Dangerous Dog"

        # 4) Собираем метаданные в data URI
        metadata = {
            "name":        name,
            "symbol":      ticker,
            "description": summary,
            "external_url": url,
            "image":       image_url
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
