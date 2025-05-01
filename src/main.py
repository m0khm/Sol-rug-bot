import os, asyncio, logging
from dotenv import load_dotenv
from twitter_watcher import TwitterWatcher
from ai_summarizer import AISummarizer
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
                                        pump = PumpClient()
                                            notifier = TelegramNotifier(
                                                    bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
                                                            chat_id=os.getenv("TELEGRAM_CHAT_ID")
                                                                )

                                                                    async for tweet in watcher.stream_tweets():
                                                                            url = f"https://twitter.com/{tweet['author_username']}/status/{tweet['id']}"
                                                                                    logging.info(f"Новый твит: {url}")

                                                                                            summary = summarizer.summarize(tweet["text"])
                                                                                                    ticker = generate_ticker(summary)
                                                                                                            name = summary.title()
                                                                                                                    description_uri = f"data:application/json;base64,<...metadata_json...>"
                                                                                                                            # Прим.: для полной метадаты нужен JSON на Arweave/IPFS, URI передать сюда.

                                                                                                                                    result = await pump.create_token(
                                                                                                                                                name=name,
                                                                                                                                                            symbol=ticker,
                                                                                                                                                                        uri=description_uri
                                                                                                                                                                                )
                                                                                                                                                                                        logging.info(f"Создано: {result}")

                                                                                                                                                                                                notifier.notify(
                                                                                                                                                                                                            f"✅ Создан токен {name} (${ticker})\n"
                                                                                                                                                                                                                        f"Mint: {result['mint']}\n"
                                                                                                                                                                                                                                    f"BondingCurve: {result['bonding_curve']}\n"
                                                                                                                                                                                                                                                f"Tx: https://solscan.io/tx/{result['tx']}\n"
                                                                                                                                                                                                                                                            f"Твит: {url}"
                                                                                                                                                                                                                                                                    )

                                                                                                                                                                                                                                                                    if __name__ == "__main__":
                                                                                                                                                                                                                                                                        asyncio.run(main())
                                                                                                                                                                                                                                                                        