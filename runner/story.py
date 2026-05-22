from dataclasses import dataclass, field
from datetime import datetime
from logging import LoggerAdapter, getLogger
from typing import Optional, Literal

from consts.errors import StoryError
from models.story_info import StoryStatus
from providers import PROVIDER_MAP
from providers.base import BaseProvider

EMA_ALPHA = 0.3
STALE_THRESHOLD_DAYS = 45


@dataclass
class Story:
    id: str
    title: str
    source: str
    channel_id: int
    last_chapter: int
    latest_chapter_date: str
    error: Optional[StoryError] = None
    last_check_date: Optional[str] = None
    avg_days_per_chapter: Optional[float] = None

    # Attributes not written to the json file
    is_new_chapter: bool = False
    is_completed: bool = False
    new_chapters_count: int = 0
    provider: BaseProvider = None
    logger: LoggerAdapter = field(default=getLogger("story"), repr=False, compare=False)

    def __post_init__(self):
        if isinstance(self.error, str):
            try:
                self.error = StoryError(self.error)
            except ValueError:
                self.error = None

        self.provider = PROVIDER_MAP.get(self.source)
        if self.provider:
            self.provider = self.provider(self.id, self.last_chapter)
        else:
            raise ValueError(f"Provider {self.source} not found.")

        if self.last_check_date is None:
            self.last_check_date = self.latest_chapter_date

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "channel_id": self.channel_id,
            "last_chapter": self.last_chapter,
            "latest_chapter_date": self.latest_chapter_date,
            "source": self.source,
            "error": self.error.value if self.error else None,
            "last_check_date": self.last_check_date,
            "avg_days_per_chapter": self.avg_days_per_chapter,
        }

    def _get_skip_interval(self) -> int:
        avg = self.avg_days_per_chapter
        if avg is None:
            return 7
        if avg <= 2:
            return 3
        if avg <= 7:
            return 5
        if avg <= 14:
            return 7
        return 10

    def _should_skip_check(self) -> bool:
        if self.error:
            return False
        try:
            last_update = datetime.strptime(self.latest_chapter_date, "%d/%m/%Y")
            days_since_update = (datetime.today() - last_update).days
        except ValueError:
            return False
        if days_since_update < STALE_THRESHOLD_DAYS:
            return False
        try:
            last_check = datetime.strptime(self.last_check_date, "%d/%m/%Y")
            days_since_check = (datetime.today() - last_check).days
        except ValueError:
            return False
        return days_since_check < self._get_skip_interval()

    def _update_avg(self, new_ch: int, prev_ch: int, prev_date_str: str):
        chapters_added = new_ch - prev_ch
        if chapters_added <= 0:
            return
        try:
            prev_date = datetime.strptime(prev_date_str, "%d/%m/%Y")
            days_elapsed = (datetime.today() - prev_date).days
        except ValueError:
            return
        if days_elapsed <= 0:
            return
        sample = days_elapsed / chapters_added
        if self.avg_days_per_chapter is None:
            self.avg_days_per_chapter = sample
        else:
            self.avg_days_per_chapter = EMA_ALPHA * sample + (1 - EMA_ALPHA) * self.avg_days_per_chapter

    def get_latest_chapter(self):
        # Skip METRUYENCHU provider
        if self.source == "metruyenchu":
            self.logger.info(f"{self.title} -> Bỏ qua kiểm tra (METRUYENCHU)")
            return

        # Smart skip cho truyện stale
        if self._should_skip_check():
            interval = self._get_skip_interval()
            if self.avg_days_per_chapter is not None:
                self.logger.info(
                    f"{self.title} -> Bỏ qua (không update >={STALE_THRESHOLD_DAYS}d, "
                    f"avg={self.avg_days_per_chapter:.1f}d/chap, interval={interval}d)"
                )
            else:
                self.logger.info(
                    f"{self.title} -> Bỏ qua (không update >={STALE_THRESHOLD_DAYS}d, interval={interval}d)"
                )
            return

        today_str = datetime.today().strftime("%d/%m/%Y")
        try:
            story_info = self.provider.get_story_info()
            latest_chapter = story_info.latest_chapter
            if latest_chapter > 0:
                prev_ch = self.last_chapter
                prev_date = self.latest_chapter_date
                self.is_new_chapter = True
                self.new_chapters_count = latest_chapter - prev_ch
                self.last_chapter = latest_chapter
                self.latest_chapter_date = story_info.latest_chapter_date
                self.is_completed = story_info.status == StoryStatus.COMPLETED
                self._update_avg(latest_chapter, prev_ch, prev_date)
                self.display()
            elif self.error:
                self.logger.info(f"{self.title} -> Có lỗi {self.error.value} sẽ tiến hành xử lý")
            else:
                self.logger.info(f"{self.title} -> Chưa có chap mới")
        except Exception as e:
            self.logger.error(f"{self.title} -> {e}")
        finally:
            self.last_check_date = today_str

    def needs_attention(self) -> bool:
        return self.is_new_chapter or self.error is not None

    def set_error(self, error: StoryError):
        self.error = error

    def clear_error_if(self, error: StoryError):
        if self.error == error:
            self.error = None

    def resolve_or_set_error(self, success: bool, error_type: StoryError):
        if success:
            self.clear_error_if(error_type)
        else:
            self.set_error(error_type)

    def is_story_text_only(self) -> bool:
        return self.source == "metruyenchu"

    def channel_message(self, format: Literal["plain", "rich"] = "rich"):
        link = self.provider.get_link_chapter(self.last_chapter)

        if self.is_completed:
            chapter_plain = "Hoàn thành"
            chapter_rich = "**Hoàn thành**"
        else:
            if self.new_chapters_count > 1:
                chapter_plain = f"Chương {self.last_chapter} ({self.new_chapters_count} chap mới)"
                chapter_rich = f"Chương **{self.last_chapter}** (**{self.new_chapters_count}** chap mới)"
            else:
                chapter_plain = f"Chương {self.last_chapter}"
                chapter_rich = f"Chương **{self.last_chapter}**"

        if format == "rich":
            return (
                f"{chapter_rich} - **{self.latest_chapter_date}** - "
                f"[[Link-đọc]({link})]"
            )
        elif format == "plain":
            return f"{chapter_plain} - {self.latest_chapter_date}"
        else:
            raise ValueError(f"Unknown format: {format}")

    def message_channel_general(self):
        if self.is_story_text_only():
            prefix_story = "**[Truyện chữ]**"
        else:
            prefix_story = "**[Truyện tranh]**"

        return f"{prefix_story}<#{self.channel_id}> -> {self.channel_message()}"

    def display(self):
        self.logger.warning(f"{self.title} -> {self.channel_message(format='plain')}")
