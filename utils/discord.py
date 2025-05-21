import os
import requests
from typing import Any
from functools import wraps

def require_token(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.token:
            raise RuntimeError("Bot token is missing ‒ set DISCORD_BOT_TOKEN.")
        return func(self, *args, **kwargs)
    return wrapper

class DiscordClient:
    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, bot_token: str | None = None) -> None:
        self.token: str = bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if self.token:
            self.session.headers["Authorization"] = f"Bot {self.token}"

    @require_token
    def send_message(self, channel_id: int | str, content: str) -> Any:
        """
        Sends a message to a specified Discord channel.

        Args:
            channel_id (int | str): The ID of the Discord channel where the message will be sent.
            content (str): The content of the message to be sent.

        Returns:
            Any: The JSON response from the Discord API containing details of the sent message.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request to the Discord API fails.
        """
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"
        resp = self.session.post(url, json={"content": content}, timeout=10)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"[DiscordResponse] Body: {resp.text}")
            raise

        return resp.json()

    def close(self) -> None:
        self.session.close()