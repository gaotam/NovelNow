import time
from datetime import datetime
from typing import List, Dict, Tuple, Any
from utils import load_json_file, write_json_file
from consts import ProviderName
from providers.base import BaseProvider
from providers.truyenqqto import TruyenQQTOProvider
from providers.metruyenchu import MeChuyenChuProvider


class Runner:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = []
        self.providers: List[BaseProvider] = []

    @staticmethod
    def sort_by_update_date(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
            Sorts a list of data entries by the 'update_date' field in descending order (newest first).
            Args:
                data (List[Dict[str, Any]]): A list of dictionaries, where each dictionary represents
                a data entry and may contain an 'update_date' field as a string in the format "DD/MM/YYYY".
            Returns:
                List[Dict[str, Any]]: The sorted list of dictionaries, ordered by 'update_date' from newest to oldest.
        """
        def parse_date(date_str: str):
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                # Return a very old date for items with invalid dates
                return datetime(1900, 1, 1)

        return sorted(data, key=lambda x: parse_date(x.get('update_date', '')), reverse=True)

    def prepare(self):
        """
            Prepares the runner by loading data from the specified JSON file and initializing providers.

            This method reads the data from the JSON file located at `self.data_path`,
            and for each entry in the data, it checks if the provider matches `ProviderName.TRUYENQQTO`.
            If it matches, it creates an instance of `TruyenQQTOProvider` with the entry's `id` and `last_chapter`,
            and appends it to the `self.providers` list.
        """
        self.data = load_json_file(self.data_path)
        provider_map = {
            ProviderName.TRUYENQQTO.value: TruyenQQTOProvider,
            ProviderName.METRUYENCHU.value: MeChuyenChuProvider
        }

        for d in self.data:
            provider_class = provider_map.get(d['provider'])
            if provider_class:
                self.providers.append(provider_class(d['id'], d['title'], d['last_chapter']))

    def update_data(self, latest_chapter_map: Dict[str, Tuple[int, str]]):
        """
            Updates the data with the latest chapter information.
            Args:
                latest_chapter_map (Dict[str, Tuple[int, str]]): A dictionary where the keys are provider IDs (str),
                and the values are tuples containing:
                    - int: The latest chapter number.
                    - str: The update date of the latest chapter.
        """
        for d in self.data:
            if d['id'] in latest_chapter_map:
                d['last_chapter'] = latest_chapter_map[d['id']][0]
                d['update_date'] = latest_chapter_map[d['id']][1]

        write_json_file(self.data_path, Runner.sort_by_update_date(self.data))
        print("data.json updated successfully.")

    def run(self):
        """
            Executes the main workflow of the Runner.

            This method performs the following steps:
            1. Prepares the runner by loading data and initializing providers.
            2. Iterates through the providers to fetch the latest chapter information.
            3. Updates the data with the latest chapter details and writes it back to the JSON file.

            Workflow:
                - Calls `self.prepare()` to load data and initialize providers.
                - For each provider in `self.providers`, retrieves the latest chapter information using `get_latest_chapter()`.
                - If no new chapter is found (`latest_chapter == 0`), logs a message.
                - If a new chapter is found, updates `latest_chapter_map` with the provider's ID, latest chapter, and release date.
                - Calls `self.update_data()` to persist the updated data.
            """
        print("Running...")
        self.prepare()

        latest_chapter_map = {}
        for provider in self.providers:
            (latest_chapter, date_chapter) = provider.get_latest_chapter()
            if latest_chapter == 0:
                print(f"ID: {provider.title} -> Không có chương mới")
            else:
                latest_chapter_map[provider.id] = (latest_chapter, date_chapter)
                print(f"ID: {provider.title} -> Chương {latest_chapter} - Ngày cập nhật: {date_chapter}")
            time.sleep(2)
        self.update_data(latest_chapter_map)