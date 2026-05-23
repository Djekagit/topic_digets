import os
import unittest
from unittest.mock import patch

from core.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_admin_ids_are_parsed_from_comma_separated_env(self):
        with patch.dict(os.environ, {"ADMIN_IDS": "701151229, 203601147"}, clear=True):
            settings = Settings.from_env(load_dotenv_file=False)

        self.assertEqual(settings.admin_ids, [701151229, 203601147])

    def test_database_url_is_built_from_legacy_db_parts(self):
        env = {
            "USER_DB": "digest_user",
            "PASSWORD_DB": "secret",
            "DB_NAME": "topic_digests",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings.from_env(load_dotenv_file=False)

        self.assertEqual(
            settings.database_url,
            "postgresql+asyncpg://digest_user:secret@localhost/topic_digests",
        )

    def test_legacy_token_name_is_supported(self):
        with patch.dict(os.environ, {"TgToken": "legacy-token"}, clear=True):
            settings = Settings.from_env(load_dotenv_file=False)

        self.assertEqual(settings.tg_token, "legacy-token")


if __name__ == "__main__":
    unittest.main()
