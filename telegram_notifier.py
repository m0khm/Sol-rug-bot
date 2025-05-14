import requests
import logging
import asyncio

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_ids_str: str):
        if not bot_token:
            raise ValueError("Telegram bot token is required.")
        if not chat_ids_str:
            raise ValueError("Telegram chat IDs string cannot be empty.")
        
        self.bot_token = bot_token
        self.chat_ids = [chat_id.strip() for chat_id in chat_ids_str.split(",") if chat_id.strip()]
        if not self.chat_ids:
            raise ValueError("No valid Telegram chat IDs provided.")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/"
        logger.info(f"TelegramNotifier initialized for {len(self.chat_ids)} chat(s).")

    async def send_message(
        self,
        ticker: str,
        token_pump_fun_url: str,
        original_tweet_url: str,
        summary: str | None = None, # Optional summary of the tweet
        image_url: str | None = None # Optional URL of the generated image
    ) -> bool:
        """Sends a notification message to all configured Telegram chats."""
        if not ticker or not token_pump_fun_url or not original_tweet_url:
            logger.error("Ticker, token URL, and original tweet URL are required to send a Telegram notification.")
            return False

        message_lines = [
            f"🚀 New Token Created: *{ticker.replace('$', '$$')}* 🚀",
            f"\n📄 *Summary:* {summary.replace('.', '.\\.')}" if summary else "",
            f"\n🔗 *Token on Pump.fun:* [{token_pump_fun_url.replace('.', '.\\.')}]({token_pump_fun_url})",
            f"🐦 *Original Tweet:* [{original_tweet_url.replace('.', '.\\.')}]({original_tweet_url})",
        ]
        text = "\n".join(filter(None, message_lines))
        
        # Telegram API sendMessage endpoint
        send_url = self.base_url + "sendMessage"
        all_sent_successfully = True

        for chat_id in self.chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "MarkdownV2", # Using MarkdownV2 for better formatting
                "disable_web_page_preview": False
            }
            
            # If an image URL is provided, try to send it as a photo first, then the text message.
            # Or, include it in the text message if Telegram supports preview for it.
            # For simplicity, we will send the text message which can include the image URL for preview.
            # If a separate photo is desired, use sendPhoto endpoint.

            try:
                # Asynchronous HTTP request
                # For simplicity in this environment, using synchronous requests library in a thread or 
                # using an async http client like aiohttp would be better for a fully async app.
                # Given the current toolset, we will use synchronous requests for now.
                # This means this method isn't truly async if called directly without an async http client.
                # However, the overall bot structure is async.
                
                # Simulating async behavior for the purpose of this structure
                # In a real scenario, replace with `await http_client.post(...)`
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda: requests.post(send_url, data=payload, timeout=10))
                
                response_data = response.json()
                if response.status_code == 200 and response_data.get("ok"):
                    logger.info(f"Successfully sent notification to chat ID: {chat_id} for token {ticker}")
                else:
                    logger.error(f"Failed to send Telegram notification to {chat_id}. Status: {response.status_code}, Response: {response_data.get('description', response.text)}")
                    all_sent_successfully = False
            except requests.exceptions.RequestException as e:
                logger.error(f"Error sending Telegram message to {chat_id}: {e}")
                all_sent_successfully = False
            except Exception as e:
                logger.error(f"An unexpected error occurred while sending Telegram message to {chat_id}: {e}")
                all_sent_successfully = False
        
        return all_sent_successfully

# Example Usage (for testing purposes)
async def _test_telegram_notifier():
    logging.basicConfig(level=logging.INFO)
    # Load from .env or use hardcoded for isolated test (ensure to replace with real values for actual testing)
    # These are the user-provided values
    test_bot_token = "8088184694:AAG9MIvXoE_UX04ZnIV5rvkuivMfHppAD9Y"
    test_chat_ids = "528378450,527625531" # Comma-separated

    if "YOUR_TELEGRAM_BOT_TOKEN" in test_bot_token or not test_chat_ids:
        logger.warning("Using placeholder Telegram token or chat IDs. Notification will likely fail.")
        # return # Uncomment to prevent running with placeholder data

    notifier = TelegramNotifier(bot_token=test_bot_token, chat_ids_str=test_chat_ids)

    success = await notifier.send_message(
        ticker="$TESTCOIN",
        token_pump_fun_url="https://pump.fun/7ScejHDwzpjwwCzbEPYoDfin5Zx2VriBP1GteESApump",
        original_tweet_url="https://twitter.com/elonmusk/status/1234567890123456789",
        summary="This is a test summary for the new token generated from a tweet about space exploration and dogs\.",
        image_url="https://example.com/test_image.png" # Optional
    )

    if success:
        logger.info("[TEST] Telegram notification process completed (check your Telegram chats).")
    else:
        logger.error("[TEST] Telegram notification process encountered errors.")

if __name__ == "__main__":
    # To run this test, you need:
    # 1. A valid Telegram Bot Token and Chat ID(s).
    #    Set them in the _test_telegram_notifier function or via environment variables.
    # 2. The `requests` library: pip install requests
    asyncio.run(_test_telegram_notifier())

