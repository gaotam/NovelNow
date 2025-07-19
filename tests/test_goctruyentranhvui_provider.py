import unittest

from models.story_info import StoryStatus
from providers.goctruyentranhvui import GocTruyenTranhVuiProvider

class TestGocTruyenTranhVuiProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = GocTruyenTranhVuiProvider(id="dinh-cap-khi-van--lang-le-tu-luyen-ngan-nam", last_chapter=5)
        story_info = provider.get_story_info()
        self.assertGreater(story_info.latest_chapter, 5)
        self.assertIsNotNone(story_info.latest_chapter_date)
        self.assertEqual(story_info.status, StoryStatus.ONGOING)

    def test_completed_status_when_story_is_finished(self):
        provider = GocTruyenTranhVuiProvider(id="su-tro-lai-cua-phap-su-vi-dai-sau-4000-nam", last_chapter=212)
        story_info = provider.get_story_info()
        self.assertGreaterEqual(story_info.latest_chapter, 212)
        self.assertIsNotNone(story_info.latest_chapter_date)
        self.assertEqual(story_info.status, StoryStatus.COMPLETED)