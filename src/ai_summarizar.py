import openai

class AISummarizer:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def summarize(self, text: str, max_words: int = 3) -> str:
        prompt = (
            f"Сократи этот текст до {max_words} ключевых слов:\n\n\"{text}\""
        )
        resp = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=20,
            temperature=0.5
        )
        summary = resp.choices[0].text.strip()
        return summary
