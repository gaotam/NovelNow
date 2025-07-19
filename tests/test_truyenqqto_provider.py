import unittest

from models.story_info import StoryStatus
from providers.truyenqqto import TruyenQQTOProvider

class TestTruyenQQTOProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = TruyenQQTOProvider(id="ta-hoc-tram-than-trong-benh-vien-tam-than-15082", last_chapter=5)
        story_info = provider.get_story_info()
        self.assertGreater(story_info.latest_chapter, 5)
        self.assertIsNotNone(story_info.latest_chapter_date)

    def test_completed_status_when_story_is_finished(self):
        provider = TruyenQQTOProvider(id="multiverse-no-watashi-koishite-ii-desu-ka-16000", last_chapter=9)
        story_info = provider.get_story_info()
        self.assertGreaterEqual(story_info.latest_chapter, 10)
        self.assertIsNotNone(story_info.latest_chapter_date)
        self.assertEqual(story_info.status, StoryStatus.COMPLETED)
