import re
from datetime import date, timedelta, datetime

def iso_to_ddmmyyyy(iso_date: str) -> str:
    """
        Converts an ISO 8601 date string to the format 'dd/mm/yyyy'.
        Args:
            iso_date (str): The ISO 8601 date string to be converted.
                            Example: '2023-10-05T14:48:00Z'.
        Returns:
            str: The date in 'dd/mm/yyyy' format.
                 Example: '05/10/2023'.
    """
    dt = datetime.fromisoformat(iso_date.rstrip("Z"))
    return dt.strftime("%d/%m/%Y")


def format_date_chapter(raw_date_str: str) -> str:
    """
        Formats a raw date string into the 'dd/mm/yyyy' format.

        Args:
            raw_date_str (str): The raw date string to be formatted.
                                Examples include:
                                - '5 giờ trước' (5 hours ago)
                                - '2 ngày trước' (2 days ago)
                                - '2023-10-05'

        Returns:
            str: The formatted date string in 'dd/mm/yyyy' format.
                 Examples:
                 - '05/10/2023' for a valid ISO date or relative date.
                 - Original string with '-' replaced by '/' if no match.
        """
    raw_date_str = raw_date_str.lower().strip()

    if re.match(r"\d+\s+giờ\s+trước", raw_date_str):
        return date.today().strftime("%d/%m/%Y")

    match_day = re.match(r"(\d+)\s+ngày\s+trước", raw_date_str)
    if match_day:
        days_ago = int(match_day.group(1))
        return (date.today() - timedelta(days=days_ago)).strftime("%d/%m/%Y")

    return raw_date_str.replace('-', '/')