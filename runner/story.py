from dataclasses import dataclass, field
from datetime import datetime, timedelta
from logging import LoggerAdapter, getLogger
from typing import Literal, Optional

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
    next_check_date: Optional[str] = None
    last_success_date: Optional[str] = None
    error_count: int = 0

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

        if self.next_check_date is None:
            self.next_check_date = self.last_check_date

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
            "next_check_date": self.next_check_date,
            "last_success_date": self.last_success_date,
            "error_count": self.error_count,
        }

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            return None

    @staticmethod
    def _format_date(value: datetime) -> str:
        return value.strftime("%d/%m/%Y")

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

    def _is_stale_story(self) -> bool:
        last_update = self._parse_date(self.latest_chapter_date)
        if last_update is None:
            return False
        days_since_update = (datetime.today() - last_update).days
        return days_since_update >= STALE_THRESHOLD_DAYS

    def _get_stale_next_due_date(self) -> Optional[datetime]:
        if not self._is_stale_story():
            return None
        last_check = self._parse_date(self.last_check_date)
        if last_check is None:
            return None
        return last_check + timedelta(days=self._get_skip_interval())

    def _should_skip_check(self) -> bool:
        if self.error:
            return False
        next_due = self._get_stale_next_due_date()
        if next_due is None:
            return False
        return datetime.today().date() < next_due.date()

    def _schedule_next_check(self):
        interval = 1
        if self._is_stale_story():
            interval = self._get_skip_interval()
        self.next_check_date = self._format_date(datetime.today() + timedelta(days=interval))

    def _mark_fetch_success(self, today_str: str):
        self.last_success_date = today_str
        self.error_count = 0
        self._schedule_next_check()

    def _mark_fetch_failure(self, today_str: str):
        self.error_count += 1
        self.next_check_date = today_str

    def get_skip_reason(self) -> str | None:
        if self.source == "metruyenchu":
            return "metruyenchu"
        if self._should_skip_check():
            return "stale_interval"
        return None

    def _update_avg(self, new_ch: int, prev_ch: int, prev_date_str: str):
        chapters_added = new_ch - prev_ch
        if chapters_added <= 0:
            return
        prev_date = self._parse_date(prev_date_str)
        if prev_date is None:
            return
        days_elapsed = (datetime.today() - prev_date).days
        if days_elapsed <= 0:
            return
        sample = days_elapsed / chapters_added
        if self.avg_days_per_chapter is None:
            self.avg_days_per_chapter = sample
        else:
            self.avg_days_per_chapter = EMA_ALPHA * sample + (1 - EMA_ALPHA) * self.avg_days_per_chapter

    def get_latest_chapter(self):
        if self.source == "metruyenchu":
            self.logger.info(f"{self.title} -> Bỏ qua kiểm tra (METRUYENCHU)")
            return False

        if self._should_skip_check():
            interval = self._get_skip_interval()
            last_check = self.last_check_date or "unknown"
            next_due = self._get_stale_next_due_date()
            next_due_str = self._format_date(next_due) if next_due else (self.next_check_date or "unknown")
            if self.avg_days_per_chapter is not None:
                self.logger.info(
                    f"{self.title} -> Bỏ qua (không update >={STALE_THRESHOLD_DAYS}d, "
                    f"avg={self.avg_days_per_chapter:.1f}d/chap, recheck_after={interval}d, "
                    f"last_check={last_check}, next_due={next_due_str})"
                )
            else:
                self.logger.info(
                    f"{self.title} -> Bỏ qua (không update >={STALE_THRESHOLD_DAYS}d, recheck_after={interval}d, "
                    f"last_check={last_check}, next_due={next_due_str})"
                )
            return False

        today_str = self._format_date(datetime.today())
        try:
            story_info = self.provider.get_story_info()
            latest_chapter = story_info.latest_chapter
            if latest_chapter and latest_chapter > 0:
                prev_ch = self.last_chapter
                prev_date = self.latest_chapter_date
                self.is_new_chapter = True
                self.new_chapters_count = latest_chapter - prev_ch
                self.last_chapter = latest_chapter
                self.latest_chapter_date = story_info.latest_chapter_date
                self.is_completed = story_info.status == StoryStatus.COMPLETED
                self._update_avg(latest_chapter, prev_ch, prev_date)
                self.display()
                self._mark_fetch_success(today_str)
            elif self.error:
                self.logger.info(f"{self.title} -> Có lỗi {self.error.value} sẽ tiến hành xử lý")
                self._mark_fetch_success(today_str)
            else:
                self.logger.info(f"{self.title} -> Chưa có chap mới")
                self._mark_fetch_success(today_str)
        except Exception as e:
            self.logger.error(f"{self.title} -> {e}")
            self._mark_fetch_failure(today_str)
        finally:
            self.last_check_date = today_str
        return True

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
            return f"{chapter_rich} - **{self.latest_chapter_date}** - [[Link-đọc]({link})]"
        if format == "plain":
            return f"{chapter_plain} - {self.latest_chapter_date}"
        raise ValueError(f"Unknown format: {format}")

    def message_channel_general(self):
        prefix_story = "**[Truyện chữ]**" if self.is_story_text_only() else "**[Truyện tranh]**"
        return f"{prefix_story}<#{self.channel_id}> -> {self.channel_message()}"

    def display(self):
        self.logger.warning(f"{self.title} -> {self.channel_message(format='plain')}")
