# src/ai_image_generator.py

import os
import openai

class AIImageGenerator:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        # читаем из .env
        self.n    = int(os.getenv("IMAGE_COUNT", "1"))
        self.size = os.getenv("IMAGE_SIZE", "512x512")

    def generate_image(self, prompt: str) -> list[str]:
        """
        По текстовому промпту генерирует self.n изображений размера self.size.
        Возвращает список URL.
        """
        resp = openai.Image.create(
            prompt=prompt,
            n=self.n,
            size=self.size
        )
        return [item["url"] for item in resp["data"]]
