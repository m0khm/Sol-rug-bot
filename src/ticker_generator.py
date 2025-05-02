#src/ticker_generator.py
import re

VOWELS = set("aeiouAEIOU")

def generate_ticker(summary: str) -> str:
    words = re.findall(r"\w+", summary)
    if len(words) > 1:
        # первые буквы каждого слова
        ticker = "".join(w[0] for w in words)[:3]
    else:
        # удаляем гласные и берём первые 3 символа
        cons = [c for c in words[0] if c not in VOWELS]
        ticker = "".join(cons)[:3]
    return ticker.upper()
