import os
import asyncio
import logging
import uuid
import requests # For downloading the image
from dotenv import load_dotenv

from twitter_watcher import TwitterWatcher
from ai_processor import AIProcessor
from ticker_generator import TickerGenerator
from selenium_pump_bot import PumpSeleniumBot
from telegram_notifier import TelegramNotifier

# Setup basic logging
logging.basicConfig(level=logging.INFO, format=	'%(asctime)s - %(name)s - %(levelname)s - %(message)s		')
logger = logging.getLogger("main_bot")

async def main_workflow():
    load_dotenv()
    logger.info("Solana Auto Token Bot - Starting Main Workflow")

    # --- Load Configuration --- 
    try:
        # Twitter Config
        twitter_usernames = os.getenv("TWITTER_USERNAMES")
        poll_interval = int(os.getenv("TWEET_POLL_INTERVAL", "60"))

        # AI Config
        openai_api_key = os.getenv("OPENAI_API_KEY")

        # Pump.fun Config
        pump_fun_username = os.getenv("PUMP_FUN_USERNAME")
        pump_fun_password = os.getenv("PUMP_FUN_PASSWORD")
        solana_private_key = os.getenv("SOLANA_PRIVATE_KEY")
        initial_buy_sol = float(os.getenv("INITIAL_BUY_SOL", "0.05"))
        chrome_profile_dir = os.getenv("CHROME_PROFILE_DIR")
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "chromedriver")
        pump_headless = os.getenv("PUMP_HEADLESS", "true").lower() == "true"

        # Telegram Config
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_ids = os.getenv("TELEGRAM_CHAT_IDS")
        
        # Optional links for token creation
        token_telegram_link = os.getenv("TOKEN_TELEGRAM_LINK")
        token_website_link = os.getenv("TOKEN_WEBSITE_LINK")

        # Validate essential configurations
        if not all([twitter_usernames, openai_api_key, pump_fun_username, pump_fun_password, solana_private_key, telegram_bot_token, telegram_chat_ids]):
            logger.error("CRITICAL: Essential environment variables are missing. Please check your .env file.")
            return
        logger.info("Configuration loaded successfully.")

    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    # --- Initialize Modules --- 
    try:
        twitter_watcher = TwitterWatcher(usernames_str=twitter_usernames, poll_interval=poll_interval)
        ai_processor = AIProcessor(openai_api_key=openai_api_key)
        ticker_generator = TickerGenerator()
        pump_bot = PumpSeleniumBot(
            profile_dir=chrome_profile_dir,
            driver_path=chromedriver_path,
            headless=pump_headless,
            pump_fun_username=pump_fun_username,
            pump_fun_password=pump_fun_password,
            solana_private_key=solana_private_key
        )
        telegram_notifier = TelegramNotifier(bot_token=telegram_bot_token, chat_ids_str=telegram_chat_ids)
        logger.info("All modules initialized successfully.")
    except ValueError as ve:
        logger.error(f"Error initializing modules: {ve}")
        return
    except Exception as e:
        logger.error(f"Unexpected error during module initialization: {e}")
        return

    # --- Main Loop --- 
    try:
        logger.info("Starting to watch for new tweets...")
        async for tweet in twitter_watcher.watch():
            logger.info(f"--- New Tweet Detected --- ID: {tweet["id"]} from @{tweet["username"]}")
            logger.debug(f"Tweet content: {tweet["content"]}")

            try:
                # 1. AI Processing: Summarize, generate image prompt, image, description
                summary = await ai_processor.summarize_tweet(tweet["content"])
                if not summary or summary.startswith("Error:"):
                    logger.error(f"Failed to get valid summary for tweet {tweet["id"]}. Skipping token creation.")
                    continue
                
                image_prompt = ai_processor.generate_image_prompt(summary)
                image_url_from_ai = await ai_processor.generate_image(image_prompt)
                
                if not image_url_from_ai:
                    logger.error(f"Failed to generate image for tweet {tweet["id"]}. Skipping token creation.")
                    continue

                # Download image locally as Pump.fun likely needs an upload
                local_image_path = None
                try:
                    img_response = requests.get(image_url_from_ai, timeout=20)
                    img_response.raise_for_status()
                    image_ext = os.path.splitext(image_url_from_ai.split("?")[0])[-1] or ".png"
                    if not image_ext.startswith("."): image_ext = "." + image_ext # ensure dot
                    # ensure images directory exists (should be created by setup script or manually)
                    os.makedirs("/home/ubuntu/solana_token_bot/images", exist_ok=True)
                    local_image_path = f"/home/ubuntu/solana_token_bot/images/{uuid.uuid4()}{image_ext}"
                    with open(local_image_path, "wb") as f:
                        f.write(img_response.content)
                    logger.info(f"Image downloaded successfully to {local_image_path}")
                except Exception as img_e:
                    logger.error(f"Failed to download image from {image_url_from_ai}: {img_e}")
                    continue # Skip if image download fails

                coin_description = ai_processor.generate_coin_description(tweet["username"])

                # 2. Generate Ticker and Token Name
                ticker = ticker_generator.generate_ticker(summary) # Or tweet content
                token_name = ticker_generator.generate_token_name(summary) # Or a more descriptive name
                logger.info(f"Generated Token Name: 	'{token_name}	', Ticker: 	'{ticker}	'")

                # 3. Solana/Pump.fun Interaction
                logger.info("Connecting to Pump.fun and logging in...")
                pump_bot.connect_wallet_and_login() # This method initializes driver if needed
                
                logger.info(f"Attempting to create token on Pump.fun: {token_name} ({ticker})")
                token_pump_fun_url = pump_bot.create_token(
                    token_name=token_name,
                    token_ticker=ticker,
                    description=coin_description,
                    image_path=local_image_path,
                    tweet_url=tweet["url"],
                    initial_buy_sol=initial_buy_sol,
                    token_telegram_link=token_telegram_link,
                    token_website_link=token_website_link
                )

                if local_image_path and os.path.exists(local_image_path):
                    try: os.remove(local_image_path)
                    except OSError as e: logger.warning(f"Could not remove temporary image {local_image_path}: {e}")

                if not token_pump_fun_url:
                    logger.error(f"Failed to create token on Pump.fun for tweet {tweet["id"]}.")
                    # pump_bot.close() # Close driver on failure to allow restart for next tweet
                    continue
                
                logger.info(f"Token successfully created on Pump.fun: {token_pump_fun_url}")

                # 4. Telegram Notification
                logger.info(f"Sending Telegram notification for token {ticker}...")
                await telegram_notifier.send_message(
                    ticker=ticker,
                    token_pump_fun_url=token_pump_fun_url,
                    original_tweet_url=tweet["url"],
                    summary=summary,
                    image_url=image_url_from_ai # Send the AI URL, not local path
                )
                logger.info(f"--- Successfully processed tweet ID: {tweet["id"]} ---")

            except Exception as e_inner:
                logger.error(f"Error processing tweet ID {tweet.get('id', 'N/A')}: {e_inner}", exc_info=True)
                # Ensure temporary image is cleaned up if it exists and an error occurs mid-process
                if 'local_image_path' in locals() and local_image_path and os.path.exists(local_image_path):
                    try: os.remove(local_image_path)
                    except OSError as e_cleanup: logger.warning(f"Could not remove temporary image {local_image_path} during error handling: {e_cleanup}")
            finally:
                # Consider if pump_bot.close() should be here or managed differently for multiple tweets
                # For now, let's assume it's managed per token creation or at the end of the script.
                # If connect_wallet_and_login is called per tweet, then close should also be per tweet or handled by PumpBot class internally.
                # The current PumpSeleniumBot is designed to be re-used, so closing might be better done at the very end.
                pass 

    except KeyboardInterrupt:
        logger.info("Bot operation stopped by user (Ctrl+C).")
    except Exception as e_outer:
        logger.error(f"An unexpected error occurred in the main loop: {e_outer}", exc_info=True)
    finally:
        logger.info("Shutting down Solana Auto Token Bot.")
        if pump_bot and pump_bot.driver: # Ensure driver exists before trying to close
            pump_bot.close()
        logger.info("Bot has been shut down.")

if __name__ == "__main__":
    # Ensure .env file is in the same directory or parent directory as this script, or specify path to load_dotenv()
    # Example: load_dotenv(dotenv_path="/path/to/your/.env")
    # The modules (twitter_watcher.py, etc.) should be in the same directory or in PYTHONPATH.
    asyncio.run(main_workflow())

