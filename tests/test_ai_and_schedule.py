import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from services.ai import TELEGRAM_MARKDOWN_SYSTEM_PROMPT, build_chat_messages, build_prompt
from services.schedule import calculate_next_digest_at, is_group_due


class AIAndScheduleTest(unittest.IsolatedAsyncioTestCase):
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

    def test_chat_messages_include_strict_telegram_markdown_system_prompt(self):
        messages = build_chat_messages("Digest prompt")

        self.assertEqual(
            messages,
            [
                {"role": "system", "content": TELEGRAM_MARKDOWN_SYSTEM_PROMPT},
                {"role": "user", "content": "Digest prompt"},
            ],
        )
        self.assertIn("Telegram MarkdownV2", TELEGRAM_MARKDOWN_SYSTEM_PROMPT)
        self.assertIn("без вступления", TELEGRAM_MARKDOWN_SYSTEM_PROMPT)

    def test_default_prompt_demands_ready_telegram_markdown_without_preamble(self):
        from storage.models import DEFAULT_PROMPT

        self.assertIn("Telegram MarkdownV2", DEFAULT_PROMPT)
        self.assertIn("без вступления", DEFAULT_PROMPT)
        self.assertIn("[текст](https://example.com)", DEFAULT_PROMPT)

    async def test_existing_legacy_default_prompt_is_upgraded(self):
        from storage.models import AISettings, DEFAULT_PROMPT, LEGACY_DEFAULT_PROMPT, ensure_default_ai_settings

        class FakeResult:
            def scalar_one_or_none(self):
                return AISettings(provider="openrouter", model="model", default_prompt=LEGACY_DEFAULT_PROMPT)

        class FakeSession:
            def __init__(self):
                self.flushed = False

            async def execute(self, statement):
                return FakeResult()

            async def flush(self):
                self.flushed = True

        session = FakeSession()

        ai_settings = await ensure_default_ai_settings(session)

        self.assertEqual(ai_settings.default_prompt, DEFAULT_PROMPT)
        self.assertTrue(session.flushed)

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
