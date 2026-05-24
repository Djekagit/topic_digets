import unittest

from aiogram.enums.parse_mode import ParseMode

from bot.helper import save_send


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class BotHelperTest(unittest.IsolatedAsyncioTestCase):
    async def test_save_send_uses_telegram_markdown_v2_parse_mode(self):
        bot = FakeBot()

        await save_send("[Источник](https://example.com)", bot, 123)

        self.assertEqual(bot.messages[0]["parse_mode"], ParseMode.MARKDOWN_V2)


if __name__ == "__main__":
    unittest.main()
