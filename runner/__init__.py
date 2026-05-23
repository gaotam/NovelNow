import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from consts.errors import StoryError
from logger import PrefixAdapter, setup_logger
from utils import chunk_by_size, load_json_file, write_json_file
from utils.config import get_config, load_config_project
from utils.datetime import get_time_now_format
from utils.discord import DiscordClient

from .story import Story

logger = setup_logger()

TRACKING_PATH = "story_tracking.json"
TRACKING_DB_PATH = "story_tracking.db"
MAX_TRACKING_SNAPSHOTS = 30
JSON_SYNC_INTERVAL_DAYS = 3
APP_STATE_LAST_JSON_SYNC = "last_json_sync_date"


class Runner:
    def __init__(self, db_path: str | None = None, data_path: str | None = None):
        load_config_project()
        self.data_path = data_path or get_config("common.data_path")
        self.db_path = db_path or TRACKING_DB_PATH
        self.discord_client = DiscordClient(get_config("discord.bot_token"))
        self.stories: List[Story] = []
        self.last_fetch_summary = {"fetched": 0, "skip_stale": 0, "skip_source": 0}
        self._init_db()
        self._bootstrap_stories_from_json()

    @staticmethod
    def sort_by_update_date(data: List[Story]) -> List[Story]:
        def parse_date(date_str: str):
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                return datetime(1900, 1, 1)

        return sorted(data, key=lambda x: parse_date(x.latest_chapter_date), reverse=True)

    def _connect_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _db(self):
        conn = self._connect_db()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    last_chapter INTEGER NOT NULL,
                    latest_chapter_date TEXT NOT NULL,
                    error TEXT,
                    last_check_date TEXT,
                    avg_days_per_chapter REAL,
                    next_check_date TEXT,
                    last_success_date TEXT,
                    error_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS story_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    avg_days_per_chapter REAL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(channel_id, snapshot_date)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

    def _bootstrap_stories_from_json(self):
        with self._db() as conn:
            has_story = conn.execute("SELECT 1 FROM stories LIMIT 1").fetchone()
            if has_story:
                return

        data_file = Path(self.data_path)
        if not data_file.exists():
            return

        data = load_json_file(self.data_path)
        if not isinstance(data, list):
            return

        stories = [Story(**item) for item in data]
        self._save_stories(stories)
        logger.info(f"✅ Đã migrate {len(stories)} truyện từ data.json sang SQLite.")

    @staticmethod
    def _row_to_story(row: sqlite3.Row) -> Story:
        return Story(
            id=row["id"],
            title=row["title"],
            source=row["source"],
            channel_id=row["channel_id"],
            last_chapter=row["last_chapter"],
            latest_chapter_date=row["latest_chapter_date"],
            error=row["error"],
            last_check_date=row["last_check_date"],
            avg_days_per_chapter=row["avg_days_per_chapter"],
            next_check_date=row["next_check_date"],
            last_success_date=row["last_success_date"],
            error_count=row["error_count"] or 0,
        )

    def _save_stories(self, stories: List[Story]):
        payload = [story.to_dict() for story in stories if not story.is_completed]

        with self._db() as conn:
            active_ids = set()
            for story_data in payload:
                active_ids.add(story_data["id"])
                conn.execute(
                    """
                    INSERT INTO stories (
                        id, title, source, channel_id, last_chapter, latest_chapter_date,
                        error, last_check_date, avg_days_per_chapter, next_check_date,
                        last_success_date, error_count
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title = excluded.title,
                        source = excluded.source,
                        channel_id = excluded.channel_id,
                        last_chapter = excluded.last_chapter,
                        latest_chapter_date = excluded.latest_chapter_date,
                        error = excluded.error,
                        last_check_date = excluded.last_check_date,
                        avg_days_per_chapter = excluded.avg_days_per_chapter,
                        next_check_date = excluded.next_check_date,
                        last_success_date = excluded.last_success_date,
                        error_count = excluded.error_count
                    """,
                    (
                        story_data["id"],
                        story_data["title"],
                        story_data["source"],
                        story_data["channel_id"],
                        story_data["last_chapter"],
                        story_data["latest_chapter_date"],
                        story_data["error"],
                        story_data["last_check_date"],
                        story_data["avg_days_per_chapter"],
                        story_data["next_check_date"],
                        story_data["last_success_date"],
                        story_data["error_count"],
                    ),
                )

            if active_ids:
                placeholders = ",".join("?" for _ in active_ids)
                conn.execute(f"DELETE FROM stories WHERE id NOT IN ({placeholders})", tuple(active_ids))
            else:
                conn.execute("DELETE FROM stories")

    def _get_app_state(self, key: str) -> str | None:
        with self._db() as conn:
            row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def _set_app_state(self, key: str, value: str):
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO app_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def _sync_db_to_json_if_due(self, stories: List[Story]):
        today = datetime.today()
        last_sync_str = self._get_app_state(APP_STATE_LAST_JSON_SYNC)
        if last_sync_str:
            try:
                last_sync = datetime.strptime(last_sync_str, "%d/%m/%Y")
                if (today - last_sync).days < JSON_SYNC_INTERVAL_DAYS:
                    return
            except ValueError:
                pass

        data = [story.to_dict() for story in Runner.sort_by_update_date(stories) if not story.is_completed]
        write_json_file(self.data_path, data)
        self._set_app_state(APP_STATE_LAST_JSON_SYNC, today.strftime("%d/%m/%Y"))
        logger.info(f"✅ Đồng bộ SQLite -> data.json thành công.[{get_time_now_format()}]")

    def fetch_latest_chapters(self):
        skip_source = [s for s in self.stories if s.get_skip_reason() == "metruyenchu"]
        skip_stale = [s for s in self.stories if s.get_skip_reason() == "stale_interval"]
        will_check = len(self.stories) - len(skip_source) - len(skip_stale)
        self.last_fetch_summary = {
            "fetched": will_check,
            "skip_stale": len(skip_stale),
            "skip_source": len(skip_source),
        }
        logger.info(
            f"📋 Fetch plan: {len(self.stories)} tổng"
            f" | ✅ sẽ check: {will_check}"
            f" | ⏭️ stale skip: {len(skip_stale)}"
            f" | ⏭️ metruyenchu: {len(skip_source)}"
        )

        if skip_stale:
            preview = ", ".join(
                f"{story.title} (next_due={story._format_date(story._get_stale_next_due_date()) if story._get_stale_next_due_date() else 'unknown'})"
                for story in skip_stale[:5]
            )
            if len(skip_stale) > 5:
                preview += f", ... +{len(skip_stale) - 5} truyện"
            logger.info(f"⏭️ Stale schedule preview: {preview}")

        remaining_requests = will_check
        for index, story in enumerate(self.stories):
            prefix = f"[{index + 1}/{len(self.stories)}] - "
            story.logger = PrefixAdapter(logger, {"prefix": prefix})
            attempted = story.get_latest_chapter()
            if attempted:
                remaining_requests -= 1
                if remaining_requests > 0:
                    time.sleep(get_config("common.story_fetch_delay_sec"))

    def prepare(self):
        with self._db() as conn:
            rows = conn.execute("SELECT * FROM stories").fetchall()
        self.stories = [self._row_to_story(row) for row in rows]

    def update_data(self):
        uncompleted_stories = [story for story in self.stories if not story.is_completed]
        ordered_stories = Runner.sort_by_update_date(uncompleted_stories)
        self._save_stories(ordered_stories)
        self._sync_db_to_json_if_due(ordered_stories)
        logger.info(f"✅ SQLite cập nhật thành công.[{get_time_now_format()}]")

    def update_tracking(self):
        today_str = datetime.today().strftime("%d/%m/%Y")
        story_channel_map = {story.id: str(story.channel_id) for story in self.stories}
        self._migrate_tracking_json_to_db(story_channel_map)

        with self._db() as conn:
            for story in self.stories:
                if not story.is_new_chapter:
                    continue

                channel_key = str(story.channel_id)
                conn.execute(
                    """
                    INSERT INTO story_snapshots (channel_id, snapshot_date, chapter, avg_days_per_chapter)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(channel_id, snapshot_date)
                    DO UPDATE SET
                        chapter = excluded.chapter,
                        avg_days_per_chapter = excluded.avg_days_per_chapter
                    """,
                    (channel_key, today_str, story.last_chapter, story.avg_days_per_chapter),
                )

                conn.execute(
                    """
                    DELETE FROM story_snapshots
                    WHERE channel_id = ?
                      AND id NOT IN (
                        SELECT id
                        FROM story_snapshots
                        WHERE channel_id = ?
                        ORDER BY id DESC
                        LIMIT ?
                      )
                    """,
                    (channel_key, channel_key, MAX_TRACKING_SNAPSHOTS),
                )

    def _migrate_tracking_json_to_db(self, story_id_to_channel: Dict[str, str]):
        try:
            tracking = load_json_file(TRACKING_PATH)
        except Exception:
            return

        if not isinstance(tracking, dict) or not tracking:
            return

        with self._db() as conn:
            already_migrated = conn.execute("SELECT 1 FROM story_snapshots LIMIT 1").fetchone()
            if already_migrated:
                return

            for key, value in tracking.items():
                channel_id = story_id_to_channel.get(key, str(key))
                snapshots = value.get("snapshots", []) if isinstance(value, dict) else []
                normalized = []
                for snap in snapshots:
                    if normalized and normalized[-1].get("date") == snap.get("date"):
                        normalized[-1] = snap
                    else:
                        normalized.append(snap)

                for snap in normalized[-MAX_TRACKING_SNAPSHOTS:]:
                    conn.execute(
                        """
                        INSERT INTO story_snapshots (channel_id, snapshot_date, chapter, avg_days_per_chapter)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(channel_id, snapshot_date)
                        DO UPDATE SET
                            chapter = excluded.chapter,
                            avg_days_per_chapter = excluded.avg_days_per_chapter
                        """,
                        (
                            channel_id,
                            snap.get("date"),
                            snap.get("chapter"),
                            snap.get("avg_days_per_chapter"),
                        ),
                    )

    def send_story_channels(self, stories: List[Story]):
        filtered_stories = [s for s in stories if s.error is None or s.error == StoryError.SEND_DISCORD_PER_STORY]
        story_send_delay_sec = get_config("discord.story_send_delay_sec")

        for story in filtered_stories:
            try:
                self.discord_client.send_message(story.channel_id, story.channel_message())
                story.clear_error_if(StoryError.SEND_DISCORD_PER_STORY)
            except Exception:
                story.set_error(StoryError.SEND_DISCORD_PER_STORY)

            if story is not filtered_stories[-1]:
                time.sleep(story_send_delay_sec)

    def send_general_channel(self, stories: List[Story]):
        filtered_stories = [s for s in stories if s.error is None or s.error == StoryError.SEND_DISCORD_GENERAL]
        if not filtered_stories:
            return

        header = f"**📢 BẢN TIN CẬP NHẬT CÔNG PHÁP! [{get_time_now_format()}]**"
        channel_id = get_config("discord.general_channel_id")

        sorted_stories = Runner.sort_by_update_date(filtered_stories)
        chunk_stories = chunk_by_size(sorted_stories, get_config("discord.general_channel_chunk_size"))

        for i, chunk in enumerate(chunk_stories):
            success = True
            lines = [story.message_channel_general() for story in chunk]
            message = header + "\n" + "\n".join(lines) if i == 0 else "\n".join(lines)

            try:
                self.discord_client.send_message(channel_id, message)
                logger.info(f"✅ Gửi thông báo vào kênh chung thành công. (chunk {i + 1}/{len(chunk_stories)}).")
            except Exception:
                success = False

            for part_story in chunk:
                part_story.resolve_or_set_error(success, StoryError.SEND_DISCORD_GENERAL)

            time.sleep(get_config("discord.general_send_delay_sec"))

    def confirm_and_send_discord(self, time_format: str):
        if not get_config("discord.bot_token"):
            logger.warning("⚠️ Bot token không được cấu hình. Bỏ qua gửi thông báo.")
            return

        stories_to_process = self.get_stories_to_process()

        if not stories_to_process:
            logger.info("🚫 Không truyện nào có chương mới.")
            return

        logger.warning(f"Số truyện có chương mới: {len(stories_to_process)} truyện.")
        self.log_output_console(stories_to_process, time_format)

        choice = input("Bạn muốn gửi vào Discord? [y/N]: ").strip().lower()
        if choice == "y":
            self.send_general_channel(stories_to_process)
            self.send_story_channels(stories_to_process)

    def get_stories_to_process(self):
        return [s for s in self.stories if s.needs_attention()]

    @staticmethod
    def log_output_console(stories_to_process, time_format: str):
        if len(stories_to_process) > 0:
            filtered_stories = [
                s for s in stories_to_process if s.error is None or s.error == StoryError.SEND_DISCORD_GENERAL
            ]
            sorted_stories = Runner.sort_by_update_date(filtered_stories)

            text_stories = [s for s in sorted_stories if s.is_story_text_only()]
            comic_stories = [s for s in sorted_stories if s not in text_stories]

            total_stories_update = len(sorted_stories)
            text_stories_number = len(text_stories)
            comic_stories_number = len(comic_stories)

            message1 = "\n\n ---------------Danh sách truyện update"
            message1 += f"({text_stories_number} truyện chữ, {comic_stories_number} truyện tranh)"
            message1 += "---------------\n\n"

            if text_stories:
                message1 += f"📖 TRUYỆN CHỮ({text_stories_number}):\n"
                for i, st in enumerate(text_stories, 1):
                    lines = f"{i:>3}. {st.title} -> {st.channel_message(format='plain')}"
                    message1 += lines + "\n"
                message1 += "\n"

            if comic_stories:
                message1 += f"🎨 TRUYỆN TRANH({comic_stories_number}):\n"
                for i, st in enumerate(comic_stories, 1):
                    lines = f"{i:>3}. {st.title} -> {st.channel_message(format='plain')}"
                    message1 += lines + "\n"

            message1 += "\n---------------------------------------------------------\n"
            message1 += f"=> {total_stories_update} truyện có chap mới - Thời gian check: {time_format}"
            logger.info(message1)

    def run(self):
        start_time = time.time()
        logger.info("🚀 Đang khởi động...")
        self.prepare()
        self.fetch_latest_chapters()

        elapsed = time.time() - start_time
        time_format = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        logger.info(f"⏱ Thời gian chạy: {time_format}")
        logger.info(
            "📊 Fetch summary: "
            f"đã fetch {self.last_fetch_summary['fetched']}, "
            f"skip stale {self.last_fetch_summary['skip_stale']}, "
            f"skip source {self.last_fetch_summary['skip_source']}"
        )

        self.confirm_and_send_discord(time_format)
        self.update_data()
        self.update_tracking()
