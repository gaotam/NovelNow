import requests
from .base import BaseProvider
from datetime import date
from consts.enpoint import TRUYENQQTO_ENPOINT
from typing import Optional
from utils import extract_chapter_number

class TruyenQQTOProvider(BaseProvider):
    def __init__(self, id: str, last_chapter: int = 0):
        self.id = id
        self.last_chapter = last_chapter

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
        try:
            url = f"{TRUYENQQTO_ENPOINT}/{self.id}"
            res = requests.get(url)
            res.raise_for_status()
            return res.text
        except requests.RequestException as e:
            print(f"Error fetching HTML: {e}")
            return None

    def get_latest_chapter(self) -> (int, str):
        """
        Retrieves the latest chapter information for the current provider.

        This method fetches the HTML content of the provider's page, parses it to extract
        the latest chapter number and its release date, and compares it with the last known chapter.

        Returns:
            tuple:
                - int: The latest chapter number. Returns 0 if the latest chapter matches the last known chapter.
                - str: The release date of the latest chapter in string format. Returns an empty string if no new chapter is found.

        Workflow:
            1. Fetches the HTML content using `fetch_html`.
            2. Parses the HTML content using the `parse_html` method from the base class.
            3. If the parsed content is `None`, returns the last known chapter and today's date.
            4. Extracts the latest chapter number and release date from the parsed HTML.
            5. Compares the latest chapter with the last known chapter and returns the appropriate values.
        """
        html = self.fetch_html()
        soup = super().parse_html(html)
        if soup is None:
            return self.last_chapter, date.today()

        chapter_item = soup.select_one(".works-chapter-item")
        latest_chapter = extract_chapter_number(chapter_item.select_one(".name-chap a").get_text(strip=True))
        date_chapter = chapter_item.select_one(".time-chap").get_text(strip=True)
        return (0, "") if latest_chapter == self.last_chapter else (latest_chapter, date_chapter)
