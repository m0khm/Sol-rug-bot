import openai

class AIImageGenerator:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def generate_image(self, prompt: str, n: int = 1, size: str = "512x512") -> list[str]:
        """
        По текстовому промпту генерирует n изображений размера size.
        Возвращает список URL.
        """
        resp = openai.Image.create(
            prompt=prompt,
            n=n,
            size=size
        )
        return [item["url"] for item in resp["data"]]
