import unittest

from pydantic import ValidationError

from app.modules.telegram_module.schemas import NewsletterRequest
from app.modules.telegram_module.utils.newsletter import build_newsletter_payload


class NewsletterRequestValidationTests(unittest.TestCase):
    def test_inline_button_requires_exactly_one_target(self) -> None:
        # both url and callback_data -> invalid
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x", "url": "http://a", "callback_data": "c"}],
                }
            )
        # neither -> invalid
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x"}],
                }
            )
        # exactly one -> valid
        ok = NewsletterRequest.model_validate(
            {
                "filters": {},
                "text": "hi",
                "use_buttons": "INLINE",
                "buttons": [{"text": "x", "url": "https://example.com"}],
            }
        )
        self.assertEqual(ok.use_buttons, "INLINE")

    def test_inline_button_rejects_invalid_url(self) -> None:
        # Хост без TLD / чужая схема — Telegram отклонит («Wrong HTTP URL»).
        bad_urls = (
            "https://asdasd",  # одно-словный хост без точки
            "https://localhost",  # localhost — тоже без TLD
            "example.com",  # нет схемы
            "ftp://example.com",  # чужая схема
            "javascript:alert(1)",  # не http(s)/tg
            "https://.com",  # пустая метка
        )
        for bad_url in bad_urls:
            with self.assertRaises(ValidationError, msg=bad_url):
                NewsletterRequest.model_validate(
                    {
                        "filters": {},
                        "text": "hi",
                        "use_buttons": "INLINE",
                        "buttons": [{"text": "x", "url": bad_url}],
                    }
                )
        # Нормальные ссылки проходят.
        good_urls = (
            "https://example.com",
            "http://sub.example.co.uk",
            "https://1.2.3.4",  # IPv4
            "tg://resolve?domain=durov",  # deep-link
        )
        for good_url in good_urls:
            req = NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x", "url": good_url}],
                }
            )
            self.assertEqual(req.buttons[0].url, good_url)

    def test_inline_button_callback_data_byte_limit(self) -> None:
        # Ровно 64 ASCII-байта — на границе, валидно.
        ok = NewsletterRequest.model_validate(
            {
                "filters": {},
                "text": "hi",
                "use_buttons": "INLINE",
                "buttons": [{"text": "x", "callback_data": "a" * 64}],
            }
        )
        self.assertEqual(len(ok.buttons[0].callback_data), 64)
        # 65 ASCII-байт — за лимитом.
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x", "callback_data": "a" * 65}],
                }
            )
        # Кириллица: 33 символа × 2 байта = 66 байт > 64. Символов мало, но
        # считаем именно БАЙТЫ — поэтому отклоняем.
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {
                    "filters": {},
                    "text": "hi",
                    "use_buttons": "INLINE",
                    "buttons": [{"text": "x", "callback_data": "я" * 33}],
                }
            )

    def test_buttons_require_use_buttons_and_vice_versa(self) -> None:
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {"filters": {}, "text": "hi", "buttons": [{"text": "x"}]}
            )
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {"filters": {}, "text": "hi", "use_buttons": "INLINE"}
            )

    def test_defaults(self) -> None:
        req = NewsletterRequest.model_validate({"text": "hi"})
        self.assertIsNone(req.use_buttons)
        self.assertIsNone(req.buttons)
        self.assertIsNone(req.filters.search)


class BuildPayloadTests(unittest.TestCase):
    def test_payload_shape(self) -> None:
        req = NewsletterRequest.model_validate(
            {
                "filters": {"search": "ru", "field": "language_code"},
                "text": "hello",
                "use_buttons": "INLINE",
                "buttons": [{"text": "Site", "url": "https://example.com"}],
            }
        )
        payload = build_newsletter_payload(
            chat_ids=[1, 2, 3],
            request=req,
            file_id=42,
            broadcast_id="bcast-x",
            chunk_index=0,
            chunk_total=1,
        )
        self.assertEqual(payload["chat_ids"], [1, 2, 3])
        self.assertEqual(payload["message"], "hello")
        self.assertEqual(payload["use_buttons"], "INLINE")
        self.assertEqual(
            payload["buttons"], [{"text": "Site", "url": "https://example.com"}]
        )
        self.assertEqual(payload["file_id"], 42)
        self.assertEqual(payload["broadcast_id"], "bcast-x")
        self.assertEqual(payload["chunk_index"], 0)
        self.assertEqual(payload["chunk_total"], 1)

    def test_payload_no_buttons_no_file(self) -> None:
        req = NewsletterRequest.model_validate({"text": "hello"})
        payload = build_newsletter_payload(
            chat_ids=[1],
            request=req,
            file_id=None,
            broadcast_id="bcast-y",
            chunk_index=2,
            chunk_total=5,
        )
        self.assertIsNone(payload["buttons"])
        self.assertIsNone(payload["file_id"])
        self.assertIsNone(payload["use_buttons"])
