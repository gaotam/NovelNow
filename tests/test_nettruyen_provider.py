import unittest

from models.chapter import Status
from providers import NetTruyenProvider
from providers.truyenqqto import TruyenQQTOProvider

class TestNetTruyenProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = NetTruyenProvider(id="hoa-than-thanh-meo", last_chapter=5)
        chapter_info = provider.get_latest_chapter()
        self.assertGreater(chapter_info.latest_chapter, 5)
        self.assertIsNotNone(chapter_info.date)

    # def test_completed_status_when_story_is_finished(self):
    #     provider = NetTruyenProvider(id="su-tro-lai-cua-phap-su-vi-dai-sau-4000-nam", last_chapter=212)
    #     chapter_info = provider.get_latest_chapter()
    #     self.assertGreaterEqual(chapter_info.latest_chapter, 212)
    #     self.assertIsNotNone(chapter_info.date)
    #     self.assertEqual(chapter_info.status, Status.COMPLETED)