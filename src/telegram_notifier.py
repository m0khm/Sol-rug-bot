#src/telegram_notifier.py
from telegram import Bot

class TelegramNotifier:
    """
    Рассылает одно и то же сообщение в несколько чатов.
    """

    def __init__(self, bot_token: str, chat_ids: list[str]):
        self.bot = Bot(token=bot_token)
        self.chat_ids = chat_ids

    def notify(self, text: str, parse_mode: str = None):
        for cid in self.chat_ids:
            self.bot.send_message(chat_id=cid, text=text, parse_mode=parse_mode)
