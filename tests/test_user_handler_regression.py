import inspect
import unittest

from bot.handlers import user_handlers


class UserHandlerRegressionTest(unittest.TestCase):
    def test_default_prompt_creation_uses_callback_actor_not_bot_message_author(self):
        source = inspect.getsource(user_handlers.create_default_prompt_callback)
        old_call = "_finish_group_creation(callback.message, state, " + "custom_prompt=None)"

        self.assertIn("callback.from_user", source)
        self.assertNotIn(old_call, source)

    def test_finish_group_creation_requires_explicit_telegram_user(self):
        signature = inspect.signature(user_handlers._finish_group_creation)

        self.assertIn("telegram_user", signature.parameters)


if __name__ == "__main__":
    unittest.main()
