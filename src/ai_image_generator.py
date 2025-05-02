# src/ai_image_generator.py

import os
import openai


class AIImageGenerator:
    """
    Генерирует n изображений размера size через Images API (DALL·E).
    Параметры берутся из .env (IMAGE_COUNT, IMAGE_SIZE).
    """

    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.n = int(os.getenv("IMAGE_COUNT", "1"))
        self.size = os.getenv("IMAGE_SIZE", "512x512")

    async def generate(self, prompt: str) -> list[str]:
        resp = await openai.Image.acreate(prompt=prompt, n=self.n, size=self.size)
        return [item["url"] for item in resp["data"]]
