from typing import Optional
from .base import BaseProvider
from consts import ProviderName
from consts.enpoint import ENDPOINTS
from models.story_info import StoryInfo, StoryStatus
from utils import extract_chapter_number
from utils.datetime import iso_to_ddmmyyyy

class MeChuyenChuProvider(BaseProvider):
    def __init__(self, id: str, last_chapter: int = 0):
        """
            Initializes the MeChuyenChuProvider instance.
            Args:
                id (str): The unique identifier for the provider.
                last_chapter (int, optional): The last chapter number. Defaults to 0.
        """
        self.novel_link = ""
        self.latest_chapter = 0
        super().__init__(id, last_chapter)

    def fetch_api(self) -> Optional[dict]:
        params = {
            "filter[book_id]": self.id,
            "filter[type]": "published"
        }

        res = super().request_get(ENDPOINTS[ProviderName.METRUYENCHU], params=params)
        return res.json() if res else None

    def get_story_info(self) -> StoryInfo:
        """
        Retrieves detailed information about the story, including the latest chapter, its release date, and status.

        This method fetches the HTML content of the story page, parses it to extract the latest chapter information,
        and determines the story's status (e.g., ongoing or completed). If the latest chapter matches the previously
        recorded chapter, an empty `StoryInfo` object is returned.
        """
        res = self.fetch_api()
        if not res or 'extra' not in res or 'book' not in res['extra'] or not res['data']:
            return StoryInfo.empty()

        book_info = res['extra']['book']
        self.novel_link = book_info.get('link', "")
        self.latest_chapter = book_info.get('latest_index', 0)
        latest_chapter_info = res['data'][-1]
        latest_chapter = extract_chapter_number(latest_chapter_info.get('name', ""))
        if latest_chapter == self.last_chapter:
            return StoryInfo.empty()

        latest_chapter_date = iso_to_ddmmyyyy(latest_chapter_info.get('published_at', ""))
        status = StoryStatus.COMPLETED if res['extra']['book']['status'] == 2 else StoryStatus.ONGOING
        return StoryInfo(latest_chapter, latest_chapter_date, status)

    def get_link_chapter(self, chapter: int) -> str:
        """
        Constructs the URL for a specific chapter of the comic.

        Args:
            chapter (int): The chapter number for which the URL is to be constructed.

        Returns:
            str: The URL for the specified chapter.
        """
        return f"{self.novel_link}/chuong-{self.latest_chapter}"