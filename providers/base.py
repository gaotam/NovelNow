from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
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

    @abstractmethod
    def __init__(self, id: str, title: str, last_chapter: int = 0):
        """
            Initializes the BaseProvider instance.

            Args:
                id (str): The unique identifier for the provider.
                title (str): The title of the content.
                last_chapter (int, optional): The last chapter number. Defaults to 0.
        """
        self.id = id
        self.title = title
        self.last_chapter = last_chapter

    @abstractmethod
    def get_latest_chapter(self) -> (int, str):
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