import time
from .story import Story
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from utils import load_json_file, write_json_file

class Runner:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.stories: List[Story] = []

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
    
    def print_new_chapters_grouped_by_source(self) -> None:
        """
        Prints new chapters grouped by their source.

        This method filters the stories to include only those with new chapters,
        groups them by their source, and then prints the grouped stories. Each
        group is displayed with its source name followed by the details of the
        stories in that group.
        """
        filtered_stories = [story for story in self.stories if story.is_new_chapter]
        grouped_stories = defaultdict(list)
        for story in filtered_stories:
            grouped_stories[story.source].append(story)

        for source, story_list in grouped_stories.items():
            print(f"\n🌟 Source: {source}")
            for story in story_list:
                story.display()

    def prepare(self):
        """
        Prepares the stories by loading data from a JSON file and initializing
        Story objects.
        """
        data = load_json_file(self.data_path)
        self.stories = [Story(**d) for d in data]

    def update_data(self):
        """
        Updates the data file with the latest story information.

        This method iterates through the list of stories, converts each story
        to a dictionary representation, and writes the updated list of stories
        to a JSON file. The stories are sorted by their update date before
        being written to the file.

        The method also prints a confirmation message upon successful update.

        Raises:
            Exception: If there is an issue writing to the JSON file.
        """
        data = []
        for story in self.stories:  
            data.append(story.to_dict())

        write_json_file(self.data_path, Runner.sort_by_update_date(data))
        print("✅ data.json updated successfully.")

    def run(self):
        print("🚀 Running...")
        self.prepare()

        for story in self.stories:
            story.get_latest_chapter()
            time.sleep(1.4)                

        self.print_new_chapters_grouped_by_source()
        self.update_data()