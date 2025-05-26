import requests
from typing import Optional
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

    def get_latest_chapter(self) -> tuple[int, str]:
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
            return 0, ""

        chapter_item = soup.select_one("#chapter_list > li")
        latest_chapter = extract_chapter_number(chapter_item.select_one("div.chapter a").get_text(strip=True))
        date_chapter = format_date_chapter(chapter_item.select_one("div.col-xs-4.no-wrap.small.text-center").get_text(strip=True))

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
        return f"{ENDPOINTS[ProviderName.NETTRUYEN]}/{self.id}/chuong-{chapter}"