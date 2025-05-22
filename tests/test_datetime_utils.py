import unittest
from datetime import date, timedelta
from utils.datetime import format_date_chapter
from dateutil.relativedelta import relativedelta


class TestFormatDateChapter(unittest.TestCase):
    def test_formats_relative_date_in_hours_or_minutes(self):
        result = format_date_chapter("5 giờ trước")
        self.assertEqual(result, date.today().strftime("%d/%m/%Y"))

    def test_formats_relative_date_in_days(self):
        result = format_date_chapter("2 ngày trước")
        self.assertEqual(result, (date.today() - timedelta(days=2)).strftime("%d/%m/%Y"))

    def test_formats_relative_date_in_months(self):
        result = format_date_chapter("3 tháng trước")
        self.assertEqual(result, (date.today() - relativedelta(months=3)).strftime("%d/%m/%Y"))

    def test_formats_iso_date_correctly(self):
        result = format_date_chapter("05-10-2023")
        self.assertEqual(result, "05/10/2023")

    def test_returns_original_string_if_no_match(self):
        result = format_date_chapter("invalid-date")
        self.assertEqual(result, "invalid/date")