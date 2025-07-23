from dataclasses import dataclass, field
from typing import Optional, Literal
from logging import LoggerAdapter, getLogger

from models.story_info import StoryStatus
from providers import PROVIDER_MAP
from consts.errors import StoryError
from providers.base import BaseProvider

@dataclass
class Story:
    id: str
    title: str
    source: str
    channel_id: int
    last_chapter: int
    latest_chapter_date: str
    error: Optional[StoryError] = None

    # Attributes not written to the json file
    is_new_chapter: bool = False
    is_completed: bool = False
    new_chapters_count: int = 0
    provider: BaseProvider = None
    logger: LoggerAdapter = field(default=getLogger("story"), repr=False, compare=False)

    def __post_init__(self):
        """
        Post-initialization method for the class. This method sets up the provider
        based on the source attribute using the PROVIDER_MAP. If a matching provider
        is found, it initializes the provider with the given id and last_chapter.
        If no matching provider is found, it raises a ValueError.
        """
        if isinstance(self.error, str):
            try:
                self.error = StoryError(self.error)
            except ValueError:
                self.error = None

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
                - "latest_chapter_date" (Any): The date when the story was last updated.
                - "source" (Any): The source of the story.
        """
        return {
            "id": self.id,
            "title": self.title,
            "channel_id": self.channel_id,
            "last_chapter": self.last_chapter,
            "latest_chapter_date": self.latest_chapter_date,
            "source": self.source,
            "error": self.error.value if self.error else None,
        }

    def get_latest_chapter(self):
        """
        Retrieves the latest chapter information from the provider and updates the story's state.

        This method fetches the latest chapter number and its associated date from the provider.
        If a new chapter is available (i.e., the chapter number is greater than 0), it updates
        the `last_chapter` and `latest_chapter_date` attributes of the story, sets the `is_new_chapter`
        flag to True, and triggers the display of the updated information.
        """
        try:
            story_info = self.provider.get_story_info()
            latest_chapter = story_info.latest_chapter
            if latest_chapter > 0:
                self.is_new_chapter = True
                self.new_chapters_count = latest_chapter - self.last_chapter
                self.last_chapter = latest_chapter
                self.latest_chapter_date = story_info.latest_chapter_date
                self.is_completed = story_info.status == StoryStatus.COMPLETED
                self.display()
            elif self.error:
                self.logger.info(f"{self.title} -> Có lỗi {self.error.value} sẽ tiến hành xử lý")
            else:
                self.logger.info(f"{self.title} -> Chưa có chap mới")
        except Exception as e:
            self.logger.error(f"{self.title} -> {e}")

    def needs_attention(self) -> bool:
        """
        Determines if the story requires attention.

        This method checks if the story has new chapters or if there is an error
        associated with it. If either condition is true, the story is flagged as
        needing attention.

        Returns:
            bool: True if the story has new chapters or an error, otherwise False.
        """
        return self.is_new_chapter or self.error is not None

    def set_error(self, error: StoryError):
        """
        Sets the error attribute for the story.

        Args:
            error (StoryError): The error to be assigned to the story.
        """
        self.error = error

    def clear_error_if(self, error: StoryError):
        """
        Clears the error attribute if it matches the specified error.
        Args:
            error (StoryError): The error to check against the current error.
        """
        if self.error == error:
            self.error = None

    def resolve_or_set_error(self, success: bool, error_type: StoryError):
        """
        Resolves or sets an error based on the success status.

        If the operation is successful, it clears the specified error. Otherwise,
        it sets the error attribute to the given error type.

        Args:
            success (bool): Indicates whether the operation was successful.
            error_type (StoryError): The type of error to set if the operation fails.
        """
        if success:
            self.clear_error_if(error_type)
        else:
            self.set_error(error_type)

    def channel_message(self, format: Literal["plain", "rich"] = "rich"):
        """
        Generates a formatted message for the story's latest chapter.

        This method creates a message string based on the specified format, either "plain" or "rich".
        The message includes details about the latest chapter, the number of new chapters, the update date,
        and a link to the chapter if the "rich" format is selected.

        Args:
            format (Literal["plain", "rich"]): The format of the message.
                - "plain": Returns a simple text message.
                - "rich": Returns a message with rich formatting, including a bold text and a clickable link.

        Returns:
            str: A formatted message string containing the latest chapter information.

        Raises:
            ValueError: If the specified format is not "plain" or "rich".
        """
        link = self.provider.get_link_chapter(self.last_chapter)

        if self.is_completed:
            chapter_plain = "Hoàn thành"
            chapter_rich = "**Hoàn thành**"
        else:
            if self.new_chapters_count > 1:
                chapter_plain = f"Chương {self.last_chapter} ({self.new_chapters_count} chap mới)"
                chapter_rich = f"Chương **{self.last_chapter}** (**{self.new_chapters_count}** chap mới)"
            else:
                chapter_plain = f"Chương {self.last_chapter}"
                chapter_rich = f"Chương **{self.last_chapter}**"

        if format == "rich":
            return (
                f"{chapter_rich} - Ngày cập nhật: **{self.latest_chapter_date}** - "
                f"[[Link-đọc]({link})]"
            )
        elif format == "plain":
            return f"{chapter_plain} - {self.latest_chapter_date}"
        else:
            raise ValueError(f"Unknown format: {format}")

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
        self.logger.warning(f"{self.title} -> {self.channel_message(format='plain')}")