from dataclasses import dataclass

from logger import setup_logger
from providers import PROVIDER_MAP
from providers.base import BaseProvider

logger = setup_logger()

@dataclass
class Story:
    id: str
    title: str
    last_chapter: int
    update_date: str
    source: str
    channel_id: int
    new_chapter: int = 0
    is_new_chapter: bool = False
    provider: BaseProvider = None

    def __post_init__(self):
        """
        Post-initialization method for the class. This method sets up the provider
        based on the source attribute using the PROVIDER_MAP. If a matching provider
        is found, it initializes the provider with the given id and last_chapter.
        If no matching provider is found, it raises a ValueError.
        """
        self.provider = PROVIDER_MAP.get(self.source)
        if self.provider:
            self.provider = self.provider(self.id, self.last_chapter)
        else:
            raise ValueError(f"Provider {self.source} not found.")

    def to_dict(self):
        """
        Converts the story object into a dictionary representation.

        Returns:
            dict: A dictionary containing the following key-value pairs:
                - "id" (Any): The unique identifier of the story.
                - "title" (str): The title of the story.
                - "last_chapter" (Any): Information about the last chapter of the story.
                - "update_date" (Any): The date when the story was last updated.
                - "source" (Any): The source of the story.
        """
        return {
            "id": self.id,
            "title": self.title,
            "channel_id": self.channel_id,
            "last_chapter": self.last_chapter,
            "update_date": self.update_date,
            "source": self.source
        }

    def get_latest_chapter(self):
        """
        Retrieves the latest chapter information from the provider and updates the story's state.

        This method fetches the latest chapter number and its associated date from the provider.
        If a new chapter is available (i.e., the chapter number is greater than 0), it updates
        the `last_chapter` and `update_date` attributes of the story, sets the `is_new_chapter`
        flag to True, and triggers the display of the updated information.
        """
        try:
            latest_chapter, date_chapter = self.provider.get_latest_chapter()
            if latest_chapter > 0:
                self.new_chapter = latest_chapter - self.last_chapter
                self.last_chapter = latest_chapter
                self.update_date = date_chapter
                self.is_new_chapter = True
                self.display()
            else:
                logger.info(f"{self.title} -> Chưa có chap mới")
        except Exception as e:
            logger.error(f"{self.title} -> {e}")

    def channel_message(self):
        """
        Generates a message string based on the story's chapter information.

        This method checks if there are multiple new chapters available. If so, it
        includes the number of new chapters in the message. Otherwise, it returns
        a message with the last chapter information.

        Returns:
            str: A formatted message string containing the chapter information and
                 the update date.
        """
        link = self.provider.get_link_chapter(self.last_chapter)
        if self.new_chapter > 1:
            return f"Chương **{self.last_chapter}** ({self.new_chapter} chap mới) - Ngày cập nhật: **{self.update_date}** - [[Link-đọc]({link})]"
        return f"Chương **{self.last_chapter}** - Ngày cập nhật: **{self.update_date}** - [[Link-đọc]({link})]"

    def channel_general(self):
        """
        Generates a message for the channel.

        This method creates a message string that includes the story's title and
        the latest chapter information. The message is formatted for display in
        a channel or chat application.

        Returns:
            str: A formatted message string containing the story's title and latest chapter information.
        """
        return f"<#{self.channel_id}> -> {self.channel_message()}"

    def display(self):
        logger.info(f"{self.title} -> {self.channel_message()}")