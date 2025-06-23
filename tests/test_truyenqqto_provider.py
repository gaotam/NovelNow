import unittest
from providers.truyenqqto import TruyenQQTOProvider

class TestTruyenQQTOProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = TruyenQQTOProvider(id="ta-hoc-tram-than-trong-benh-vien-tam-than-15082", last_chapter=5)
        latest_chapter, latest_date = provider.get_latest_chapter()
        self.assertGreater(latest_chapter, 5)
        self.assertIsNotNone(latest_date)