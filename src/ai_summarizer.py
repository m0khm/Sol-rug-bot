# src/ai_summarizer.py

import openai

class AISummarizer:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def summarize(self, text: str, max_words: int = 3) -> str:
        """
        Сжимает текст до max_words ключевых слов,
        используя ChatCompletion с моделью o4-mini.
        """
        resp = openai.ChatCompletion.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": "You are a concise summarizer."},
                {
                    "role": "user",
                    "content": f"Сократи этот текст до {max_words} ключевых слов:\n\n\"{text}\""
                }
            ],
            temperature=0.5,
            max_tokens=20
        )
        return resp.choices[0].message.content.strip()
