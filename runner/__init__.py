import time
from datetime import datetime
from typing import List, Dict

from consts.errors import StoryError
from logger import setup_logger, PrefixAdapter
from utils import load_json_file, write_json_file, chunk_by_size
from utils.config import get_config, load_config_project
from utils.datetime import get_time_now_format
from utils.discord import DiscordClient
from .story import Story

logger = setup_logger()

TRACKING_PATH = "story_tracking.json"
MAX_TRACKING_SNAPSHOTS = 30


class Runner:
    def __init__(self):
        load_config_project()
        self.data_path = get_config('common.data_path')
        self.discord_client = DiscordClient(get_config('discord.bot_token'))
        self.stories: List[Story] = []

    @staticmethod
    def sort_by_update_date(data: List[Story]) -> List[Story]:
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

        return sorted(data, key=lambda x: parse_date(x.latest_chapter_date), reverse=True)

    def fetch_latest_chapters(self):
        skip_source = [s for s in self.stories if s.source == "metruyenchu"]
        skip_stale = [s for s in self.stories if s.source != "metruyenchu" and s._should_skip_check()]
        will_check = len(self.stories) - len(skip_source) - len(skip_stale)
        logger.info(
            f"📋 Fetch plan: {len(self.stories)} tổng"
            f" | ✅ sẽ check: {will_check}"
            f" | ⏭️  stale skip: {len(skip_stale)}"
            f" | ⏭️  metruyenchu: {len(skip_source)}"
        )

        for index, story in enumerate(self.stories):
            prefix = f"[{index + 1}/{len(self.stories)}] - "
            story.logger = PrefixAdapter(logger, {"prefix": prefix})
            story.get_latest_chapter()
            if index < len(self.stories) - 1:  # Avoid delay after the last story
                time.sleep(get_config("common.story_fetch_delay_sec"))

    def prepare(self):
        data = load_json_file(self.data_path)
        self.stories = [Story(**d) for d in data]

    def update_data(self):
        uncompleted_stories = [story for story in self.stories if not story.is_completed]
        data = [story.to_dict() for story in Runner.sort_by_update_date(uncompleted_stories)]
        write_json_file(self.data_path, data)
        logger.info(f"✅ data.json cập nhật thành công.[{get_time_now_format()}]")

    def update_tracking(self):
        try:
            tracking = load_json_file(TRACKING_PATH)
        except Exception:
            tracking = {}

        # Normalize old format:
        # - old key: story.id
        # - new key: str(channel_id)
        # - keep only snapshots
        story_id_to_channel = {story.id: str(story.channel_id) for story in self.stories}
        normalized_tracking: Dict[str, Dict] = {}
        for key, value in tracking.items():
            normalized_key = story_id_to_channel.get(key, str(key))
            snapshots = value.get("snapshots", []) if isinstance(value, dict) else []
            entry = normalized_tracking.setdefault(normalized_key, {"snapshots": []})
            entry["snapshots"].extend(snapshots)

        today_str = datetime.today().strftime("%d/%m/%Y")
        for story in self.stories:
            if not story.is_new_chapter:
                continue
            channel_key = str(story.channel_id)
            entry = normalized_tracking.setdefault(channel_key, {"snapshots": []})
            new_snapshot = {
                "date": today_str,
                "chapter": story.last_chapter,
                "avg_days_per_chapter": story.avg_days_per_chapter,
            }

            snapshots = entry["snapshots"]
            # If already has a snapshot today, update latest record instead of appending.
            if snapshots and snapshots[-1].get("date") == today_str:
                snapshots[-1] = new_snapshot
            else:
                snapshots.append(new_snapshot)

            if len(snapshots) > MAX_TRACKING_SNAPSHOTS:
                entry["snapshots"] = snapshots[-MAX_TRACKING_SNAPSHOTS:]

        write_json_file(TRACKING_PATH, normalized_tracking)

    def send_story_channels(self, stories: List[Story]):
        filtered_stories = [s for s in stories if s.error is None or s.error == StoryError.SEND_DISCORD_PER_STORY]
        story_send_delay_sec = get_config('discord.story_send_delay_sec')

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
        channel_id = get_config('discord.general_channel_id')

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

            time.sleep(get_config('discord.general_send_delay_sec'))

    def confirm_and_send_discord(self, time_format: str):
        if not get_config('discord.bot_token'):
            logger.warning("⚠️ Bot token không được cấu hình. Bỏ qua gửi thông báo.")
            return

        stories_to_process = self.get_stories_to_process()

        if not stories_to_process:
            logger.info(f"🚫 Không truyện nào có chương mới.")
            return

        logger.warning(f"Số truyện có chương mới: {len(stories_to_process)} truyện.")

        self.log_output_console(stories_to_process, time_format)

        # print("----------Đã load xong dữ liệu, tiến hành gửi vào discord----------")
        choice = input("Bạn muốn gửi vào Discord? [y/N]: ").strip().lower()
        if choice == 'y':
            self.send_general_channel(stories_to_process)
            self.send_story_channels(stories_to_process)

    def get_stories_to_process(self):
        return [s for s in self.stories if s.needs_attention()]

    @staticmethod
    def log_output_console(stories_to_process, time_format: str):
        if len(stories_to_process) > 0:
            filtered_stories = [s for s in stories_to_process if
                                s.error is None
                                or s.error == StoryError.SEND_DISCORD_GENERAL]
            sorted_stories = Runner.sort_by_update_date(filtered_stories)

            # Separate stories into text-only and comic categories
            text_stories = [s for s in sorted_stories if s.is_story_text_only()]
            comic_stories = [s for s in sorted_stories if s not in text_stories]

            total_stories_update = len(sorted_stories)
            text_stories_number = len(text_stories)
            comic_stories_number = len(comic_stories)

            message1 = f"\n\n ---------------Danh sách truyện update"
            message1 += f"({text_stories_number} truyện chữ, {comic_stories_number} truyện tranh)"
            message1 += "---------------\n\n"
            # Display text-only stories
            if text_stories:
                message1 += f"📖 TRUYỆN CHỮ({text_stories_number}):\n"
                for i, st in enumerate(text_stories, 1):
                    lines = f"{i:>3}. {st.title} -> {st.channel_message(format='plain')}"
                    message1 += lines + "\n"
                message1 += "\n"

            # Display comic stories
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
        logger.info(f"🚀 Đang khởi động...")
        self.prepare()
        self.fetch_latest_chapters()

        elapsed = time.time() - start_time
        time_format = time.strftime('%H:%M:%S', time.gmtime(elapsed))
        logger.info(f"⏱ Thời gian chạy: {time_format}")

        self.confirm_and_send_discord(time_format)
        self.update_data()
        self.update_tracking()
