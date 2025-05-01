from telegram import Bot

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    def notify(self, text: str):
        self.bot.send_message(chat_id=self.chat_id, text=text)
