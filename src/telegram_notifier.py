from telegram import Bot
import os

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_ids: list[str]):
        self.bot = Bot(token=bot_token)
        # Приводим все ID к строкам (или int, на ваш вкус)
        self.chat_ids = [cid.strip() for cid in chat_ids]

    def notify(self, text: str, parse_mode: str = None):
        for chat_id in self.chat_ids:
            self.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
