import inspect
import unittest

from bot.handlers import user_handlers
from bot.keyboards.user import group_menu_kb
from services.digest import DigestResult


class ManualDigestRegressionTest(unittest.TestCase):
    def test_group_menu_has_manual_digest_action(self):
        source = inspect.getsource(group_menu_kb)

        self.assertIn("group:digest_now:", source)

    def test_manual_digest_callback_parses_channels_before_processing(self):
        source = inspect.getsource(user_handlers.group_digest_now_callback)

        self.assertIn("parse_channels", source)
        self.assertIn("process_due_group", source)

    def test_digest_result_tracks_posts_and_sent_status(self):
        result = DigestResult(posts_count=2, sent=True)

        self.assertEqual(result.posts_count, 2)
        self.assertTrue(result.sent)


if __name__ == "__main__":
    unittest.main()
