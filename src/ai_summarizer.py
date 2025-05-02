# src/ai_summarizer.py

import openai

class AISummarizer:
    """
    Сокращает текст до 3 ключевых слов с помощью o4-mini.
    """

    def __init__(self, api_key: str, model: str = "o4-mini"):
        openai.api_key = api_key
        self.model = model

    async def summarize(self, text: str, max_words: int = 3) -> str:
        resp = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a concise summarizer."},
                {
                    "role": "user",
                    "content": f"Сократи этот текст до {max_words} ключевых слов:\n\n\"{text.strip()}\""
                }
            ],
            temperature=0.5,
            max_tokens=20
        )
        return resp.choices[0].message.content.strip()

