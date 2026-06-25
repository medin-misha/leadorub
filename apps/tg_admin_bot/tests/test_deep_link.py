import unittest

from app.modules.system.deep_link import SOURCE_PREFIX, parse_source


class ParseSourceTests(unittest.TestCase):
    def test_extracts_value_after_prefix(self) -> None:
        self.assertEqual(parse_source("source_instagram"), "instagram")

    def test_keeps_inner_underscores(self) -> None:
        # Префикс срезается только один раз — внутренние '_' остаются частью source.
        self.assertEqual(parse_source("source_telegram_ads"), "telegram_ads")

    def test_none_payload_returns_none(self) -> None:
        self.assertIsNone(parse_source(None))

    def test_empty_payload_returns_none(self) -> None:
        self.assertIsNone(parse_source(""))

    def test_payload_without_prefix_returns_none(self) -> None:
        self.assertIsNone(parse_source("instagram"))

    def test_prefix_with_empty_tail_returns_none(self) -> None:
        self.assertIsNone(parse_source(SOURCE_PREFIX))

    def test_value_is_truncated_to_column_limit(self) -> None:
        long_value = "x" * 300
        result = parse_source(f"{SOURCE_PREFIX}{long_value}")
        assert result is not None
        self.assertEqual(len(result), 255)


if __name__ == "__main__":
    unittest.main()
