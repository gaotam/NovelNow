from typing import Optional
from models.story_info import StoryInfo, StoryStatus
from .base import BaseProvider
from consts import ProviderName
from consts.enpoint import ENDPOINTS
from utils import extract_chapter_number
from utils.datetime import format_date_chapter

class NetTruyenProvider(BaseProvider):
    def __init__(self, id: str, last_chapter: int = 0):
        """
            Initializes the NetTruyenProvider instance.
            Args:
                id (str): The unique identifier for the provider.
                last_chapter (int, optional): The last chapter number. Defaults to 0.
        """
        super().__init__(id, last_chapter)

    def fetch_html(self) -> Optional[str]:
        """
            Abstract method to retrieve the latest chapter information.

            This method must be implemented by subclasses of `BaseProvider`.
            It is expected to return the latest chapter number and its release date.

            Returns:
                tuple:
                    - int: The latest chapter number.
                    - str: The release date of the latest chapter in string format.
        """

        url = f"{ENDPOINTS[ProviderName.NETTRUYEN]}/{self.id}"
        res = super().request_get(url)
        return res.text if res else None

    def get_story_info(self) -> StoryInfo:
        """"
        Retrieves detailed information about the story, including the latest chapter, its release date, and status.

        This method fetches the HTML content of the story page, parses it to extract the latest chapter information,
        and determines the story's status (e.g., ongoing or completed). If the latest chapter matches the previously
        recorded chapter, an empty `StoryInfo` object is returned.
        """
        html = self.fetch_html()
        soup = super().parse_html(html)
        if soup is None:
            return StoryInfo.empty()

        chapter_item = soup.select_one("#chapter_list > li")
        latest_chapter = extract_chapter_number(chapter_item.select_one("div.chapter a").get_text(strip=True))
        if latest_chapter == self.last_chapter:
            return StoryInfo.empty()

        latest_chapter_date = format_date_chapter(chapter_item.select_one("div.col-xs-4.no-wrap.small.text-center").get_text(strip=True))
        return StoryInfo(latest_chapter, latest_chapter_date, StoryStatus.ONGOING) # TODO: Handle completed status if applicable

    def get_link_chapter(self, chapter: int) -> str:
        """
        Constructs the URL for a specific chapter of the comic.

        Args:
            chapter (int): The chapter number for which the URL is to be constructed.

        Returns:
            str: The URL for the specified chapter.
        """
        return f"{ENDPOINTS[ProviderName.NETTRUYEN]}/{self.id}/chuong-{chapter}"