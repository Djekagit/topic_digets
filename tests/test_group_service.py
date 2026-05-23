import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from storage.requests.group import update_group_interval, update_group_prompt


class GroupServiceTest(unittest.TestCase):
    def test_update_group_interval_reschedules_from_now(self):
        group = SimpleNamespace(interval_hours=24, next_digest_at=None)
        now = datetime(2026, 5, 21, 12, 0, 0)

        update_group_interval(group, interval_hours=6, now=now)

        self.assertEqual(group.interval_hours, 6)
        self.assertEqual(group.next_digest_at, now + timedelta(hours=6))

    def test_update_group_prompt_strips_text_and_allows_reset(self):
        group = SimpleNamespace(custom_prompt=None)

        update_group_prompt(group, "  Custom {posts}  ")
        self.assertEqual(group.custom_prompt, "Custom {posts}")

        update_group_prompt(group, None)
        self.assertIsNone(group.custom_prompt)


if __name__ == "__main__":
    unittest.main()
