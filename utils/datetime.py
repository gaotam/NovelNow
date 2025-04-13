from datetime import datetime

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