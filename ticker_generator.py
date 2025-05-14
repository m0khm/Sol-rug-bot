import re
import logging

logger = logging.getLogger(__name__)

class TickerGenerator:
    def generate_ticker(self, text: str) -> str:
        """Generates a ticker based on the input text according to specified rules."""
        if not text or not text.strip():
            logger.warning("Input text for ticker generation is empty. Returning default ticker $NUL.")
            return "$NUL" # Default or error ticker

        words = re.findall(r'\b\w+\b', text.lower()) # Extract words, convert to lowercase

        if not words:
            logger.warning(f"No words found in text 	'{text}	' for ticker generation. Returning $TXT.")
            return "$TXT"

        if len(words) >= 3:
            # First letter of each of the first three words
            ticker_base = "".join(word[0] for word in words[:3])
        elif len(words) == 2:
            # First letter of each of the two words
            ticker_base = "".join(word[0] for word in words)
        elif len(words) == 1:
            # First three letters of the single word, or the whole word if shorter
            ticker_base = words[0][:3]
        else: # Should not happen if words list is not empty
            logger.error(f"Unexpected case in ticker generation for text: 	'{text}	'. Defaulting to $ERR.")
            return "$ERR"
        
        # Ensure the ticker is uppercase and has a max length (e.g., 3-5 chars, Pump.fun might have limits)
        # For now, let's aim for 3 characters, but this might need adjustment.
        final_ticker = "$" + ticker_base.upper()[:5] # Max 5 chars after $, adjust as needed
        
        logger.info(f"Generated ticker 	'{final_ticker}	' from text 	'{text}	'")
        return final_ticker

    def generate_token_name(self, summary: str, max_length: int = 30) -> str:
        """Generates a token name from the summary, ensuring it's not too long."""
        if not summary or not summary.strip() or summary.startswith("Error:"):
            return "New Awesome Token"
        
        # Capitalize first letter of each word, remove non-alphanumeric (except spaces)
        name = " ".join(word.capitalize() for word in re.findall(r'\b\w+\b', summary))
        if not name:
            name = "Inspired Token"
            
        return name[:max_length].strip()

# Example Usage (for testing purposes)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generator = TickerGenerator()

    test_cases = [
        "very dangerous dog",
        "hi guy",
        "a cat",
        "Elon Musk",
        "Solana to the moon!",
        "Supercalifragilisticexpialidocious",
        "X",
        "",
        "   ",
        "@#$@#%^"
    ]

    for text in test_cases:
        ticker = generator.generate_ticker(text)
        token_name = generator.generate_token_name(text if text else "Default Name")
        logger.info(f"Text: 	'{text}	' -> Ticker: 	'{ticker}	', Name: 	'{token_name}	'")
    
    # Test with summary from AI
    ai_summary = "Revolutionary Decentralized AI"
    ticker = generator.generate_ticker(ai_summary)
    token_name = generator.generate_token_name(ai_summary)
    logger.info(f"AI Summary: 	'{ai_summary}	' -> Ticker: 	'{ticker}	', Name: 	'{token_name}	'")

    ai_summary_short = "AI Future"
    ticker = generator.generate_ticker(ai_summary_short)
    token_name = generator.generate_token_name(ai_summary_short)
    logger.info(f"AI Summary: 	'{ai_summary_short}	' -> Ticker: 	'{ticker}	', Name: 	'{token_name}	'")

    ai_summary_one_word = "Future"
    ticker = generator.generate_ticker(ai_summary_one_word)
    token_name = generator.generate_token_name(ai_summary_one_word)
    logger.info(f"AI Summary: 	'{ai_summary_one_word}	' -> Ticker: 	'{ticker}	', Name: 	'{token_name}	'")

