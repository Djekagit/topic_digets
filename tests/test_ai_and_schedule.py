import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from services.ai import build_prompt
from services.schedule import calculate_next_digest_at, is_group_due


class AIAndScheduleTest(unittest.TestCase):
    def test_custom_prompt_overrides_default_prompt(self):
        prompt = build_prompt(
            default_prompt="Default: {posts}",
            custom_prompt="Custom summary\n{posts}",
            posts_text="Post A",
        )

        self.assertEqual(prompt, "Custom summary\nPost A")

    def test_prompt_without_placeholder_appends_posts(self):
        prompt = build_prompt(
            default_prompt="Summarize these posts",
            custom_prompt=None,
            posts_text="Post A\nPost B",
        )

        self.assertEqual(prompt, "Summarize these posts\n\nПосты:\nPost A\nPost B")

    def test_group_due_logic_uses_next_digest_at(self):
        now = datetime(2026, 5, 21, 12, 0, 0)

        self.assertTrue(is_group_due(SimpleNamespace(next_digest_at=now), now))
        self.assertTrue(is_group_due(SimpleNamespace(next_digest_at=now - timedelta(seconds=1)), now))
        self.assertFalse(is_group_due(SimpleNamespace(next_digest_at=now + timedelta(seconds=1)), now))
        self.assertFalse(is_group_due(SimpleNamespace(next_digest_at=None), now))

    def test_calculate_next_digest_at_adds_interval_hours(self):
        now = datetime(2026, 5, 21, 12, 0, 0)

        self.assertEqual(calculate_next_digest_at(now, 6), datetime(2026, 5, 21, 18, 0, 0))


if __name__ == "__main__":
    unittest.main()
