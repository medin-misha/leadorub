import re
import unicodedata
from pathlib import Path


def sanitize_filename(filename: str | None) -> str:
    """Sanitize filename to prevent Path Traversal, XSS, and DB issues."""
    if not filename:
        return "unnamed"

    # 1. Path Traversal protection: extract basename
    filename = Path(filename).name

    # 2. Normalize Unicode (NFKD)
    filename = unicodedata.normalize("NFKD", filename)

    # 3. Remove control characters (including null byte)
    filename = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", filename)

    # 4. Filter characters, allowing only alphanumeric, whitespace, dots, hyphens, and underscores.
    # \\w matches Unicode word characters (including Cyrillic)
    filename = re.sub(r"[^\w\s.-]", "_", filename)

    # 5. Deduplicate whitespace and dots
    filename = re.sub(r"\s+", " ", filename)
    filename = re.sub(r"\.+", ".", filename)

    # 6. Trim leading/trailing spaces and dots
    filename = filename.strip(" .")

    # 7. Fallback if empty or consists of dots
    if not filename or filename in (".", ".."):
        return "unnamed"

    return filename
