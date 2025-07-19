import unittest
from models.story_info import StoryStatus
from providers.metruyenchu import MeChuyenChuProvider

class TestMeChuyenChuProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = MeChuyenChuProvider(id="133656", last_chapter=5)
        story_info = provider.get_story_info()
        self.assertGreater(story_info.latest_chapter, 5)
        self.assertIsNotNone(story_info.latest_chapter_date)

    def test_completed_status_when_story_is_finished(self):
        provider = MeChuyenChuProvider(id="142758", last_chapter=1)
        story_info = provider.get_story_info()
        self.assertIsNone(story_info.latest_chapter)
        self.assertIsNotNone(story_info.latest_chapter_date)
        self.assertEqual(story_info.status, StoryStatus.COMPLETED)