import logging
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class ColorFormatter(logging.Formatter):
    COLOR_MAP = {
        logging.DEBUG: "\033[37m",     # Trắng
        logging.INFO: "\033[34m",      # Xanh dương
        logging.WARNING: "\033[33m",   # Vàng
        logging.ERROR: "\033[31m",     # Đỏ
        logging.CRITICAL: "\033[1;41m" # Trắng nền đỏ
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    color_formatter = ColorFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(color_formatter)

    file_handler = logging.FileHandler(LOG_DIR / "app.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger