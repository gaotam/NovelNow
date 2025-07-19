from dataclasses import dataclass
from enum import Enum, auto

class StoryStatus(Enum):
    ONGOING = auto()
    COMPLETED = auto()
    HIATUS = auto()
    DROPPED = auto()
    UNKNOWN = auto()

@dataclass
class StoryInfo:
    latest_chapter: int
    latest_chapter_date: str
    status: StoryStatus

    @classmethod
    def empty(cls):
        return cls(latest_chapter=0, latest_chapter_date="", status=StoryStatus.UNKNOWN)