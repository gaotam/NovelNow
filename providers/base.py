import requests
from typing import Optional
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from logger import setup_logger
from models.story_info import StoryInfo

logger = setup_logger()

class BaseProvider(ABC):
    @staticmethod
    def parse_html(html_content: str) -> BeautifulSoup:
        """
            Parses the given HTML content into a BeautifulSoup object.

            Args:
                html_content (str): The HTML content to be parsed.

            Returns:
                BeautifulSoup: A BeautifulSoup object representing the parsed HTML content.

            This method uses the 'html.parser' to parse the provided HTML string and
            returns a BeautifulSoup object for further processing.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        return soup

    @staticmethod
    def request_get(url: str, **kwargs) -> Optional[requests.Response]:
        """
            Sends a GET request to the specified URL.

            Args:
                url (str): The URL to send the GET request to.
                **kwargs: Additional keyword arguments to be passed to the requests.get() method.

            Returns:
                Optional[requests.Response]: The response object if the request is successful, None otherwise.

            This method handles exceptions that may occur during the GET request and
            prints an error message if the request fails.
        """
        try:
            res = requests.get(url, **kwargs)
            res.raise_for_status()
            return res
        except requests.RequestException as e:
            logger.error(f"GET {url} failed: {e}")
            return None

    @abstractmethod
    def __init__(self, id: str, last_chapter: int = 0):
        """
            Initializes the BaseProvider instance.

            Args:
                id (str): The unique identifier for the provider.
                last_chapter (int, optional): The last chapter number. Defaults to 0.
        """
        self.id = id
        self.last_chapter = last_chapter

    @abstractmethod
    def get_story_info(self) -> StoryInfo:
        """
            Abstract method to retrieve the latest chapter information.

            This method must be implemented by subclasses of `BaseProvider`.
            It is expected to return the latest chapter number and its release date.

            Returns:
                tuple:
                    - int: The latest chapter number.
                    - str: The release date of the latest chapter in string format.
        """
        pass

    @abstractmethod
    def get_link_chapter(self, chapter: int) -> str:
        """
            Abstract method to retrieve the link to a specific chapter.

            This method must be implemented by subclasses of `BaseProvider`.
            It is expected to return the URL for the specified chapter.

            Args:
                chapter (int): The chapter number for which the link is requested.

            Returns:
                str: The URL for the specified chapter.
        """
        pass