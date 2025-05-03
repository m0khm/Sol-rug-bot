# src/ticker_generator.py

import random
import string

class TickerGenerator:
    """
    Генератор случайного тикера из букв A–Z длины length.
    По умолчанию длина = 3 (SPL-токены обычно 3–5 символов).
    """

    def __init__(self, length: int = 3):
        """
        :param length: длина генерируемого тикера
        """
        if length < 1:
            raise ValueError("length must be >= 1")
        self.length = length

    def generate(self) -> str:
        """
        Возвращает новый случайный тикер.
        """
        return ''.join(random.choices(string.ascii_uppercase, k=self.length))
