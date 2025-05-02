#src/twitter_watcher.py
import tweepy

class TwitterWatcher:
    def __init__(self, bearer_token: str, username: str):
        self.client = tweepy.Client(bearer_token=bearer_token)
        user = self.client.get_user(username=username)
        self.user_id = user.data.id

    def stream_tweets(self):
        # установка правила фильтрации по user_id
        rules = self.client.get_stream_rules().data or []
        for r in rules:
            self.client.delete_stream_rule(r.id)
        self.client.add_stream_rule(value=f"from:{self.user_id}")

        # стрим
        stream = tweepy.StreamingClient(
            bearer_token=self.client.bearer_token,
            wait_on_rate_limit=True
        )
        stream.add_rules(tweepy.StreamRule(f"from:{self.user_id}"))
        for tweet in stream.filter(tweet_fields=["author_id", "id", "text"]):
            yield {
                "id": tweet.id,
                "text": tweet.text,
                "author_username": tweet.author_id  # заменим в main на фактическое имя
            }
