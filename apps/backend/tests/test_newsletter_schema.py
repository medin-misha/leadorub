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
                "buttons": [{"text": "x", "url": "http://a"}],
            }
        )
        self.assertEqual(ok.use_buttons, "INLINE")

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
                "buttons": [{"text": "Site", "url": "http://a"}],
            }
        )
        payload = build_newsletter_payload(chat_ids=[1, 2, 3], request=req, file_id=42)
        self.assertEqual(payload["chat_ids"], [1, 2, 3])
        self.assertEqual(payload["message"], "hello")
        self.assertEqual(payload["use_buttons"], "INLINE")
        self.assertEqual(payload["buttons"], [{"text": "Site", "url": "http://a"}])
        self.assertEqual(payload["file_id"], 42)

    def test_payload_no_buttons_no_file(self) -> None:
        req = NewsletterRequest.model_validate({"text": "hello"})
        payload = build_newsletter_payload(chat_ids=[1], request=req, file_id=None)
        self.assertIsNone(payload["buttons"])
        self.assertIsNone(payload["file_id"])
        self.assertIsNone(payload["use_buttons"])
