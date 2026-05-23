import unittest

from services.channel_utils import normalize_channel_list, normalize_channel_name, parse_interval_hours


class ChannelUtilsTest(unittest.TestCase):
    def test_normalize_channel_name_accepts_common_telegram_forms(self):
        cases = {
            "@OpenAI_News": "openai_news",
            "https://t.me/OpenAI_News": "openai_news",
            "t.me/OpenAI_News/": "openai_news",
            "https://t.me/s/OpenAI_News?before=10": "openai_news",
            "OpenAI_News": "openai_news",
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_channel_name(raw), expected)

    def test_normalize_channel_list_deduplicates_preserving_order(self):
        result = normalize_channel_list("@onech\nhttps://t.me/twoch\nonech, t.me/three")

        self.assertEqual(result, ["onech", "twoch", "three"])

    def test_private_or_invalid_channels_are_rejected(self):
        for raw in ("https://t.me/+abcdef", "https://example.com/news", "bad-name"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    normalize_channel_name(raw)

    def test_parse_interval_hours_accepts_positive_hours_only(self):
        self.assertEqual(parse_interval_hours("24"), 24)

        for value in ("0", "-1", "abc", "721"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_interval_hours(value)


if __name__ == "__main__":
    unittest.main()
