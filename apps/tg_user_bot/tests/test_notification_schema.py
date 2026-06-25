import unittest

from app.modules.notification_module.schemas import (
    TelegramButton,
    TelegramNotification,
)


class TelegramNotificationSchemaTests(unittest.TestCase):
    def test_parses_new_contract(self) -> None:
        n = TelegramNotification.model_validate(
            {
                "chat_ids": [1, 2, "3"],
                "message": "hi",
                "use_buttons": "INLINE",
                "buttons": [
                    {"text": "Site", "url": "http://a"},
                    {"text": "Cb", "callback_data": "x"},
                ],
                "file_id": 42,
            }
        )
        self.assertEqual(n.chat_ids, [1, 2, "3"])
        self.assertEqual(n.use_buttons, "INLINE")
        self.assertEqual(n.buttons[0].url, "http://a")
        self.assertEqual(n.buttons[1].callback_data, "x")
        self.assertEqual(n.file_id, 42)

    def test_optional_message_use_buttons_and_file(self) -> None:
        n = TelegramNotification.model_validate({"chat_ids": [1]})
        self.assertIsNone(n.message)
        self.assertIsNone(n.use_buttons)
        self.assertIsNone(n.buttons)
        self.assertIsNone(n.file_id)

    def test_notification_parses_broadcast_meta(self) -> None:
        n = TelegramNotification.model_validate(
            {
                "chat_ids": [1, 2],
                "message": "hi",
                "broadcast_id": "bcast-1",
                "chunk_index": 0,
                "chunk_total": 5,
            }
        )
        self.assertEqual(n.broadcast_id, "bcast-1")
        self.assertEqual(n.chunk_index, 0)
        self.assertEqual(n.chunk_total, 5)

    def test_notification_broadcast_meta_optional(self) -> None:
        # Обратная совместимость: сообщение без новых полей валидно, broadcast_id=None.
        n = TelegramNotification.model_validate({"chat_ids": [1], "message": "hi"})
        self.assertIsNone(n.broadcast_id)
        self.assertIsNone(n.chunk_index)
        self.assertIsNone(n.chunk_total)

    def test_request_contact_alias_preserved(self) -> None:
        btn = TelegramButton.model_validate({"text": "c", "request_contact": True})
        self.assertTrue(btn.requests_contect)
