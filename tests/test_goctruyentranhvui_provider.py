import unittest
from providers.goctruyentranhvui import GocTruyenTranhVuiProvider

class TestGocTruyenTranhVuiProvider(unittest.TestCase):
    def test_fetches_latest_chapter_when_data_is_valid(self):
        provider = GocTruyenTranhVuiProvider(id="dinh-cap-khi-van--lang-le-tu-luyen-ngan-nam", last_chapter=5)
        latest_chapter, latest_date = provider.get_latest_chapter()
        self.assertGreater(latest_chapter, 5)
        self.assertIsNotNone(latest_date)