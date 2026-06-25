import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.file_module import handlers
from app.modules.system import CRUD


def _file_record(name: str, link: str = "http://minio/bucket/object"):
    """File-подобный мок: .name и .link задаём явно.

    MagicMock(name=...) трактует name как имя самого мока, поэтому
    атрибут .name присваиваем отдельно.
    """
    rec = MagicMock()
    rec.name = name
    rec.link = link
    return rec


async def _empty_stream():
    """Пустой async-генератор — заглушка вместо реального S3-стрима."""
    if False:
        yield b""


class DownloadFileSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_svg_served_as_octet_stream_with_nosniff_and_attachment(
        self,
    ) -> None:
        session = MagicMock()
        record = _file_record("evil.svg")

        with (
            patch.object(CRUD, "get", AsyncMock(return_value=record)),
            patch.object(handlers.s3_client, "stream", return_value=_empty_stream()),
        ):
            response = await handlers.download_file(id=1, session=session)

        # SVG не должен отдаваться как image/svg+xml — иначе браузер
        # может отрендерить его как активный документ (Stored XSS).
        self.assertEqual(response.headers["content-type"], "application/octet-stream")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("attachment", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
