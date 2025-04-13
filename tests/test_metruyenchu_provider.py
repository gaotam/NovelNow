import unittest
from datetime import date
from providers.metruyenchu import MeChuyenChuProvider

class TestMeChuyenChuProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = MeChuyenChuProvider(id="133656", last_chapter=5)
        latest_chapter, latest_date = provider.get_latest_chapter()
        self.assertGreater(latest_chapter, 5)
        self.assertIsNotNone(latest_date)