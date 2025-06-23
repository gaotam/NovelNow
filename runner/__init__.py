import time
from datetime import datetime
from typing import List, Dict

from .story import Story
from logger import setup_logger
from utils.config import get_config
from utils.discord import DiscordClient
from utils.datetime import get_time_now_format
from utils import load_json_file, write_json_file, chunk_by_size

logger = setup_logger()


class Runner:
    def __init__(self):
        self.data_path = get_config('common.data_path')
        self.discord_client = DiscordClient(get_config('discord.bot_token'))
        self.stories: List[Story] = []

    @staticmethod
    def sort_by_update_date(data: List[Story]) -> List[Story]:
        """
            Sorts a list of data entries by the 'update_date' field in descending order (newest first).
            Args:
                data (List[Dict[str, Any]]): A list of dictionaries, where each dictionary represents
                a data entry and may contain an 'update_date' field as a string in the format "DD/MM/YYYY".
            Returns:
                List[Dict[str, Any]]: The sorted list of dictionaries, ordered by 'update_date' from newest to oldest.
        """

        def parse_date(date_str: str):
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                # Return a very old date for items with invalid dates
                return datetime(1900, 1, 1)

        return sorted(data, key=lambda x: parse_date(x.update_date), reverse=True)

    def fetch_latest_chapters(self):
        """
        Fetches the latest chapters for all stories.

        This method iterates through the list of stories and calls the `get_latest_chapter`
        method for each story to retrieve the latest chapter information. It also introduces
        a delay between each fetch operation to avoid overwhelming the server.

        Raises:
            Exception: If there is an issue fetching the latest chapter for a story.
        """
        for story in self.stories:
            story.get_latest_chapter()
            time.sleep(get_config("common.story_fetch_delay_sec"))

    def prepare(self):
        """
        Prepares the stories by loading data from a JSON file and initializing
        Story objects.
        """
        data = load_json_file(self.data_path)
        self.stories = [Story(**d) for d in data]

    def update_data(self):
        """
        Updates the data file with the latest story information.

        This method iterates through the list of stories, converts each story
        to a dictionary representation, and writes the updated list of stories
        to a JSON file. The stories are sorted by their update date before
        being written to the file.

        The method also prints a confirmation message upon successful update.

        Raises:
            Exception: If there is an issue writing to the JSON file.
        """
        data = [story.to_dict() for story in Runner.sort_by_update_date(self.stories)]
        write_json_file(self.data_path, data)
        logger.info(f"✅ data.json cập nhật thành công.[{get_time_now_format()}]")

    def send_story_channels(self, new_stories: List[Story]):
        """
        Sends a notification message to the respective Discord channels for stories with new chapters.

        This method iterates through the list of stories, checks if a story has a new chapter,
        and sends a notification message to the Discord channel associated with that story.

        Raises:
            Exception: If there is an issue sending the message to Discord.
        """
        for story in new_stories:
            self.discord_client.send_message(story.channel_id, story.channel_message())
            time.sleep(get_config('discord.story_send_delay_sec'))

    def send_general_channel(self, new_stories: List[Story]):
        """
        Sends a notification message to the general Discord channel.

        This method sends a predefined message to the general channel specified
        in the configuration. It is useful for broadcasting general updates or
        notifications.

        Raises:
            Exception: If there is an issue sending the message to Discord.
        """
        if not new_stories:
            return

        header = f"**📢 BẢN TIN CẬP NHẬT CÔNG PHÁP! [{get_time_now_format()}]**"

        channel_id = get_config('discord.general_channel_id')

        sorted_stories = Runner.sort_by_update_date(new_stories)
        chunk_stories = chunk_by_size(sorted_stories, get_config("discord.general_channel_chunk_size"))

        for i, chunk in enumerate(chunk_stories):
            lines = [story.channel_general() for story in chunk]
            message = header + "\n" + "\n".join(lines) if i == 0 else "\n".join(lines)
            self.discord_client.send_message(channel_id, message)
            time.sleep(get_config('discord.general_send_delay_sec'))

    def confirm_and_send_discord(self):
        """
        Confirms with the user and sends notifications to Discord.

        This method checks if the Discord bot token is configured. If it is,
        it prompts the user to confirm whether they want to send notifications
        to Discord. If the user confirms, it sends messages to both the general
        channel and the story-specific channels.

        Returns:
            None
        """
        if not get_config('discord.bot_token'):
            logger.warn("⚠️ Bot token không được cấu hình. Bỏ qua gửi thông báo.")
            return

        # print("----------Đã load xong dữ liệu, tiến hành gửi vào discord----------")
        choice = input("Bạn muốn gửi vào Discord? [y/N]: ").strip().lower()
        if choice == 'y':
            new_stories = [s for s in self.stories if s.is_new_chapter]
            self.send_general_channel(new_stories)
            self.send_story_channels(new_stories)
            logger.info("✅ Gửi thành công.")

    def run(self):
        logger.info(f"🚀 Đang khởi động...")
        self.prepare()
        self.fetch_latest_chapters()

        # Check if any story has a new chapter
        has_new_chapters = any(story.is_new_chapter for story in self.stories)
        if not has_new_chapters:
            logger.info(f"🚫 Không có chương mới.")
            return

        self.update_data()
        self.confirm_and_send_discord()
