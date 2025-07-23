from typing import Optional

from utils.config import get_config
from .base import BaseProvider
from consts import ProviderName
from consts.enpoint import ENDPOINTS
from utils import extract_chapter_number
from utils.datetime import format_date_chapter
from models.story_info import StoryInfo, StoryStatus

class GocTruyenTranhVuiProvider(BaseProvider):
    def __init__(self, id: str, last_chapter: int = 0):
        """
            Initializes the GocTruyenTranhVuiProvider instance.
            Args:
                id (str): The unique identifier for the provider.
                last_chapter (int, optional): The last chapter number. Defaults to 0.
        """
        self.name = ProviderName.GOCTRUYENTRANHVUI.value
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

        url = f"{ENDPOINTS[ProviderName.GOCTRUYENTRANHVUI]}/{self.id}"
        headers = {
            "User-Agent": self.config['user_agent']
        }
        cookies = {
            "cf_clearance": self.config['cf_clearance']
        }
        res = super().request_get(url, headers=headers, cookies=cookies)
        return res.text if res else None

    def get_story_info(self) -> StoryInfo:
        """
        Retrieves detailed information about the story, including the latest chapter, its release date, and status.

        This method fetches the HTML content of the story page, parses it to extract the latest chapter information,
        and determines the story's status (e.g., ongoing or completed). If the latest chapter matches the previously
        recorded chapter, an empty `StoryInfo` object is returned.
        """
        html = self.fetch_html()
        soup = super().parse_html(html)
        if soup is None:
            return StoryInfo.empty()

        chapter_item = soup.select_one("div.list.row.pa-4 > div:nth-child(1)")
        latest_chapter = extract_chapter_number(chapter_item.select_one("div.chapter-info span").get_text(strip=True))
        if latest_chapter == self.last_chapter:
            return StoryInfo.empty()

        latest_chapter_date = format_date_chapter(chapter_item.select_one("div.text--disabled div.d-flex div").get_text(strip=True))
        status_elem = soup.select_one(".information-section.pa-4 > div:nth-child(3) > span")
        status_text = status_elem.get_text(strip=True) if status_elem else ""
        status = StoryStatus.COMPLETED if "Hoàn thành" in status_text else StoryStatus.ONGOING
        return StoryInfo(latest_chapter, latest_chapter_date, status)

    def get_link_chapter(self, chapter: int) -> str:
        """
        Constructs the URL for a specific chapter of the comic.

        Args:
            chapter (int): The chapter number for which the URL is to be constructed.

        Returns:
            str: The URL for the specified chapter.
        """
        return f"{ENDPOINTS[ProviderName.GOCTRUYENTRANHVUI]}/{self.id}/chuong-{chapter}"