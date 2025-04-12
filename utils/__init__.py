import re
import json
from typing import Optional, Any

def extract_chapter_number(chapter_text: str) -> Optional[int]:
    """
        Extracts the first numeric chapter number from a given string.
        Args:
            chapter_text (str): The text containing the chapter information.
        Returns:
            Optional[int]: The extracted chapter number as an integer if found,
            otherwise `None`.
    """
    match = re.search(r'\d+', chapter_text)
    if match:
        return int(match.group())
    return None

def load_json_file(file_path: str) -> Any:
    """
        Loads and parses a JSON file from the specified file path.
        Args:
            file_path (str): The path to the JSON file to be loaded.
        Returns:
            Any: The parsed JSON data. The return type depends on the structure
            of the JSON file (e.g., it could be a dictionary, list, etc.).
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def write_json_file(file_path: str, data: Any) -> None:
    """
        Writes data to a JSON file at the specified file path.
        Args:
            file_path (str): The path to the JSON file where the data will be written.
            data (Any): The data to be serialized and written to the JSON file.
                        This can be any object that is JSON serializable.
        """
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)