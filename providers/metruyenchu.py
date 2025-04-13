import requests
from .base import BaseProvider
from consts import ProviderName
from consts.enpoint import ENDPOINTS
from typing import Optional
from utils import extract_chapter_number
from utils.datetime import iso_to_ddmmyyyy

class MeChuyenChuProvider(BaseProvider):
    def __init__(self, id: str, last_chapter: int = 0):
        self.id = id
        self.last_chapter = last_chapter

    def fetch_api(self) -> Optional[str]:
        params = {
            "filter[book_id]": self.id,
            "filter[type]": "published"
        }

        try:
            res = requests.get(ENDPOINTS[ProviderName.METRUYENCHU], params=params)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            print(f"Error fetching HTML: {e}")
            return None

    def get_latest_chapter(self) -> (int, str):
        latest_chapter_info = self.fetch_api()['data'][-1]
        latest_chapter = extract_chapter_number(latest_chapter_info['name'])
        date_chapter = iso_to_ddmmyyyy(latest_chapter_info['published_at'])
        return latest_chapter, date_chapter