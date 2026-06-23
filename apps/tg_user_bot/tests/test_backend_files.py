import unittest
from unittest.mock import patch

from app.modules.notification_module.services import backend_files


class BuildFileUrlTests(unittest.TestCase):
    def test_builds_url_from_settings(self) -> None:
        with patch.object(backend_files.settings, "backend_url", "http://backend:8000/"), \
             patch.object(backend_files.settings, "backend_api_prefix", "/api"):
            self.assertEqual(
                backend_files.build_file_url(42), "http://backend:8000/api/files/42"
            )

    def test_raises_when_backend_url_missing(self) -> None:
        with patch.object(backend_files.settings, "backend_url", None):
            with self.assertRaises(RuntimeError):
                backend_files.build_file_url(1)
