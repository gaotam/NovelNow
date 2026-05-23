import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from models.story_info import StoryInfo
from runner import APP_STATE_LAST_JSON_SYNC, Runner


class TestRunnerStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = Path(self.temp_dir.name) / "data.json"
        self.db_path = str(Path(self.temp_dir.name) / "stories.db")
        self.sample_story = {
            "id": "sample-story",
            "title": "Sample Story",
            "source": "truyenqqto",
            "channel_id": 123456,
            "last_chapter": 10,
            "latest_chapter_date": "01/05/2026",
            "error": None,
            "last_check_date": "01/05/2026",
            "avg_days_per_chapter": None,
        }
        self.data_path.write_text(json.dumps([self.sample_story], ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bootstrap_json_to_sqlite(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()

        self.assertEqual(len(runner.stories), 1)
        story = runner.stories[0]
        self.assertEqual(story.id, self.sample_story["id"])
        self.assertEqual(story.next_check_date, self.sample_story["last_check_date"])

    def test_update_data_persists_and_removes_completed_story(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()

        story = runner.stories[0]
        story.last_chapter = 11
        story.latest_chapter_date = "02/05/2026"
        story.last_check_date = "03/05/2026"
        story.next_check_date = "04/05/2026"
        story.last_success_date = "03/05/2026"
        story.error_count = 2
        runner.update_data()

        runner.prepare()
        persisted = runner.stories[0]
        self.assertEqual(persisted.last_chapter, 11)
        self.assertEqual(persisted.next_check_date, "04/05/2026")
        self.assertEqual(persisted.error_count, 2)

        persisted.is_completed = True
        runner.update_data()
        runner.prepare()
        self.assertEqual(runner.stories, [])

    def test_story_fetch_updates_scheduler_metadata(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()

        story = runner.stories[0]
        story.provider.get_story_info = lambda: StoryInfo.empty()
        attempted = story.get_latest_chapter()

        self.assertTrue(attempted)
        self.assertEqual(story.error_count, 0)
        self.assertEqual(story.last_success_date, datetime.today().strftime("%d/%m/%Y"))
        self.assertEqual(
            story.next_check_date,
            (datetime.today() + timedelta(days=1)).strftime("%d/%m/%Y"),
        )

    def test_active_story_is_not_skipped_by_next_check_date(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()

        story = runner.stories[0]
        story.latest_chapter_date = datetime.today().strftime("%d/%m/%Y")
        story.last_check_date = datetime.today().strftime("%d/%m/%Y")
        story.next_check_date = (datetime.today() + timedelta(days=1)).strftime("%d/%m/%Y")

        self.assertFalse(story._should_skip_check())

    def test_stale_story_skip_uses_last_check_plus_interval(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()

        story = runner.stories[0]
        story.latest_chapter_date = (datetime.today() - timedelta(days=60)).strftime("%d/%m/%Y")
        story.last_check_date = (datetime.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        story.next_check_date = "01/01/2000"

        next_due = story._get_stale_next_due_date()
        self.assertIsNotNone(next_due)
        self.assertEqual(next_due.strftime("%d/%m/%Y"), (datetime.today() + timedelta(days=6)).strftime("%d/%m/%Y"))
        self.assertTrue(story._should_skip_check())

    def test_update_data_skips_json_sync_when_under_3_days(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()
        runner._set_app_state(APP_STATE_LAST_JSON_SYNC, datetime.today().strftime("%d/%m/%Y"))

        original_json = self.data_path.read_text(encoding="utf-8")
        runner.stories[0].last_chapter = 77
        runner.update_data()

        current_json = self.data_path.read_text(encoding="utf-8")
        self.assertEqual(current_json, original_json)

    def test_update_data_syncs_json_when_due_3_days(self):
        runner = Runner(db_path=self.db_path, data_path=str(self.data_path))
        runner.prepare()
        due_date = (datetime.today() - timedelta(days=3)).strftime("%d/%m/%Y")
        runner._set_app_state(APP_STATE_LAST_JSON_SYNC, due_date)

        runner.stories[0].last_chapter = 88
        runner.update_data()

        exported = json.loads(self.data_path.read_text(encoding="utf-8"))
        self.assertEqual(exported[0]["last_chapter"], 88)
        self.assertEqual(
            runner._get_app_state(APP_STATE_LAST_JSON_SYNC),
            datetime.today().strftime("%d/%m/%Y"),
        )
