import time

from utils.config import Config
from utils.discord import DiscordClient
from .story import Story
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from utils import load_json_file, write_json_file

class Runner:
    def __init__(self, config: Config):
        self.data_path = config['common']['data_path']
        self.config = config
        self.discord_client = DiscordClient(config['discord']['bot_token'])
        self.stories: List[Story] = []

    @staticmethod
    def sort_by_update_date(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

        return sorted(data, key=lambda x: parse_date(x.get('update_date', '')), reverse=True)
    
    def print_new_chapters_grouped_by_source(self) -> None:
        """
        Prints new chapters grouped by their source.

        This method filters the stories to include only those with new chapters,
        groups them by their source, and then prints the grouped stories. Each
        group is displayed with its source name followed by the details of the
        stories in that group.
        """
        filtered_stories = [story for story in self.stories if story.is_new_chapter]
        grouped_stories = defaultdict(list)
        for story in filtered_stories:
            grouped_stories[story.source].append(story)

        for source, story_list in grouped_stories.items():
            print(f"\n🌟 Source: {source}")
            for story in story_list:
                story.display()

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
        data = []
        for story in self.stories:  
            data.append(story.to_dict())

        write_json_file(self.data_path, Runner.sort_by_update_date(data))
        print("✅ data.json cập nhật thành công.")


    def send_story_channels(self):
        """
        Sends a notification message to the respective Discord channels for stories with new chapters.

        This method iterates through the list of stories, checks if a story has a new chapter,
        and sends a notification message to the Discord channel associated with that story.

        Raises:
            Exception: If there is an issue sending the message to Discord.
        """
        for story in self.stories:
            if story.is_new_chapter:
                self.discord_client.send_message(story.channel_id, story.channel_message())
                time.sleep(0.2)

    def send_general_channel(self):
        """
        Sends a notification message to the general Discord channel.

        This method sends a predefined message to the general channel specified
        in the configuration. It is useful for broadcasting general updates or
        notifications.

        Raises:
            Exception: If there is an issue sending the message to Discord.
        """
        message = "📢 Bản tin cập nhật công pháp!"
        for story in self.stories:
            if story.is_new_chapter:
                message += f"\n{story.channel_general()}"
        self.discord_client.send_message(self.config['discord']['general_channel_id'], message)

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
        if not self.config['discord']['bot_token']:
            print("⚠️ Bot token không được cấu hình. Bỏ qua gửi thông báo.")
            return

        choice = input("Bạn muốn gửi vào Discord? [y/N]: ").strip().lower()
        if choice == 'y':
            self.send_general_channel()
            self.send_story_channels()
            print("✅ Gửi thành công.")

    def run(self):
        print("🚀 Đang khởi động...")
        self.prepare()

        for story in self.stories:
            story.get_latest_chapter()
            time.sleep(1.4)

        # Check if any story has a new chapter
        has_new_chapters = any(story.is_new_chapter for story in self.stories)
        if not has_new_chapters:
            print("🚫 Không có chương mới.")
            return

        self.print_new_chapters_grouped_by_source()
        self.update_data()

        self.confirm_and_send_discord()