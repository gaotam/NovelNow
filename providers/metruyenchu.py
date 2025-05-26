from typing import Optional
from .base import BaseProvider
from consts import ProviderName
from consts.enpoint import ENDPOINTS
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
        super().__init__(id, last_chapter)

    def fetch_api(self) -> Optional[dict]:
        params = {
            "filter[book_id]": self.id,
            "filter[type]": "published"
        }

        res = super().request_get(ENDPOINTS[ProviderName.METRUYENCHU], params=params)
        return res.json() if res else None

    def get_latest_chapter(self) -> tuple[int, str]:
        res = self.fetch_api()
        self.novel_link = res['extra']['book']['link']
        latest_chapter_info = res['data'][-1]
        latest_chapter = extract_chapter_number(latest_chapter_info['name'])
        date_chapter = iso_to_ddmmyyyy(latest_chapter_info['published_at'])

        if latest_chapter == self.last_chapter:
            return 0, ""
        return latest_chapter, date_chapter

    def get_link_chapter(self, chapter: int) -> str:
        """
        Constructs the URL for a specific chapter of the comic.

        Args:
            chapter (int): The chapter number for which the URL is to be constructed.

        Returns:
            str: The URL for the specified chapter.
        """
        return f"{self.novel_link}/chuong-{chapter}"