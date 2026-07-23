"""Тесты схем капельной рассылки + гарантия, что рефакторинг NewsletterContent
не изменил контракт NewsletterRequest."""

import unittest
from datetime import time

from pydantic import ValidationError

from app.modules.telegram_module.schemas import (
    DripNewsletterCreate,
    NewsletterContent,
    NewsletterRequest,
)


def make_payload(**overrides) -> dict:
    payload = {
        "trigger_state": "persona_start",
        "days_offset": 1,
        "send_time": "10:30",
        "text": "hi",
    }
    payload.update(overrides)
    return payload


class DripNewsletterCreateTests(unittest.TestCase):
    def test_parses_send_time_string(self) -> None:
        data = DripNewsletterCreate.model_validate(make_payload())
        self.assertEqual(data.send_time, time(10, 30))
        self.assertEqual(data.trigger_state, "persona_start")
        self.assertEqual(data.days_offset, 1)

    def test_negative_days_offset_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            DripNewsletterCreate.model_validate(make_payload(days_offset=-1))

    def test_empty_trigger_state_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            DripNewsletterCreate.model_validate(make_payload(trigger_state=""))

    def test_inherits_button_validation(self) -> None:
        # Кнопка INLINE с url И callback_data одновременно — невалидна,
        # как и в обычной рассылке (общий валидатор NewsletterContent).
        with self.assertRaises(ValidationError):
            DripNewsletterCreate.model_validate(
                make_payload(
                    use_buttons="INLINE",
                    buttons=[
                        {"text": "x", "url": "http://a.com", "callback_data": "c"}
                    ],
                )
            )

    def test_valid_inline_buttons_accepted(self) -> None:
        data = DripNewsletterCreate.model_validate(
            make_payload(
                use_buttons="INLINE",
                buttons=[{"text": "x", "url": "https://example.com"}],
            )
        )
        self.assertEqual(data.use_buttons, "INLINE")


class NewsletterRefactorGuardTests(unittest.TestCase):
    def test_newsletter_request_still_validates_buttons(self) -> None:
        # NewsletterRequest теперь наследует NewsletterContent — валидатор
        # кнопок должен работать как раньше.
        self.assertTrue(issubclass(NewsletterRequest, NewsletterContent))
        with self.assertRaises(ValidationError):
            NewsletterRequest.model_validate(
                {"text": "hi", "use_buttons": "INLINE", "buttons": [{"text": "x"}]}
            )

    def test_newsletter_request_keeps_filters_default(self) -> None:
        request = NewsletterRequest.model_validate({"text": "hi"})
        self.assertIsNone(request.filters.search)
        self.assertIsNone(request.filters.field)
