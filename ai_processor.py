import openai
import logging
import os

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self, openai_api_key: str):
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")
        self.api_key = openai_api_key
        openai.api_key = self.api_key

    async def summarize_tweet(self, tweet_content: str, max_summary_words: int = 10) -> str:
        """Summarizes the tweet content using OpenAI API."""
        if not tweet_content.strip():
            logger.warning("Tweet content is empty, returning empty summary.")
            return ""
        try:
            prompt = f"Summarize the following tweet in {max_summary_words} words or less, focusing on keywords that would make a good token name or theme. Extract the most impactful and memorable part. Tweet: \"" + tweet_content + "\""
            
            # Using ChatCompletion for newer models
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo", # Or a newer/cheaper model if suitable
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing tweets into very short, impactful phrases suitable for creating crypto token themes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30, # Adjusted for short summary
                temperature=0.5 # Moderately creative
            )
            summary = response.choices[0].message.content.strip()
            # Further clean up common chat model pleasantries if any
            summary = summary.replace("\"", "").replace("Sure, here's a summary: ", "").replace("Here's a summary: ", "")
            logger.info(f"Generated summary: '{summary}' for tweet: '{tweet_content[:50]}...'" )
            return summary
        except Exception as e:
            logger.error(f"Error summarizing tweet with OpenAI: {e}")
            # Fallback or re-raise as per error handling strategy
            return f"Error: Could not summarize - {tweet_content[:20]}" # Placeholder for error

    def generate_image_prompt(self, summary: str) -> str:
        """Generates an image prompt based on the summary."""
        if not summary.strip() or summary.startswith("Error:"):
            logger.warning(f"Summary is empty or an error placeholder ('{summary}'), using a generic image prompt.")
            return "A generic cryptocurrency coin logo"
        
        # Enhance the summary to make it a more descriptive prompt for DALL-E
        # Example: "A vibrant and dynamic visual representation of [summary], suitable for a crypto token logo, digital art style."
        prompt = f"A visually striking and memorable digital art image representing the theme '{summary}'. Suitable for a cryptocurrency token. Modern, clean, iconic."
        logger.info(f"Generated image prompt: '{prompt}' from summary: '{summary}'")
        return prompt

    async def generate_image(self, image_prompt: str, image_size: str = "256x256") -> str | None:
        """Generates an image using DALL-E and returns its URL."""
        try:
            response = await openai.Image.acreate(
                prompt=image_prompt,
                n=1,
                size=image_size # DALL-E supported sizes: 256x256, 512x512, or 1024x1024
            )
            image_url = response["data"][0]["url"]
            logger.info(f"Generated image URL: {image_url} for prompt: '{image_prompt}'")
            return image_url
        except Exception as e:
            logger.error(f"Error generating image with DALL-E: {e}")
            return None

    def generate_coin_description(self, twitter_username: str) -> str:
        """Generates the coin description."""
        if not twitter_username:
            return "An exciting new token inspired by a recent tweet!"
        description = f"The original token inspired by a recent tweet from @{twitter_username}."
        logger.info(f"Generated coin description: '{description}'")
        return description

# Example Usage (for testing purposes)
async def _test_ai_processor():
    logging.basicConfig(level=logging.INFO)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables for testing.")
        return

    processor = AIProcessor(openai_api_key=api_key)

    test_tweet = "Just launched a new rocket to Mars! It's a very dangerous dog, but we are hopeful for the future of humanity. #Mars #SpaceX"
    twitter_user = "elonmusk"

    summary = await processor.summarize_tweet(test_tweet)
    logger.info(f"[TEST] Summary: {summary}")

    if summary and not summary.startswith("Error:"):
        image_prompt = processor.generate_image_prompt(summary)
        logger.info(f"[TEST] Image Prompt: {image_prompt}")

        image_url = await processor.generate_image(image_prompt)
        if image_url:
            logger.info(f"[TEST] Image URL: {image_url}")
        else:
            logger.error("[TEST] Failed to generate image URL.")
    
    coin_description = processor.generate_coin_description(twitter_user)
    logger.info(f"[TEST] Coin Description: {coin_description}")

if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set in your environment to run this test
    # e.g., export OPENAI_API_KEY='your_key_here'
    # pip install openai
    asyncio.run(_test_ai_processor())

