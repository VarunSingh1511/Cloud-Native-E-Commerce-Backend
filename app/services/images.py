"""Validation of uploaded product images.

The file type is decided from the file's first bytes (its "magic number"), not
from its name or the Content-Type header: both are chosen by the client and can
be faked, e.g. a script renamed to photo.png.
"""

from dataclasses import dataclass
from typing import BinaryIO

from app.core.exceptions import BadRequestError

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB
_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class ImageType:
    """An allowed image format."""

    extension: str
    content_type: str


JPEG = ImageType("jpg", "image/jpeg")
PNG = ImageType("png", "image/png")
WEBP = ImageType("webp", "image/webp")


def detect_image_type(head: bytes) -> ImageType | None:
    """Recognise JPEG, PNG or WebP from the first 12 bytes of a file."""
    if head.startswith(b"\xff\xd8\xff"):
        return JPEG
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return WEBP
    return None


def read_limited(file: BinaryIO, limit: int = MAX_IMAGE_BYTES) -> bytes:
    """Read the whole file, but stop with a 400 as soon as it exceeds `limit` bytes."""
    data = bytearray()
    while chunk := file.read(_CHUNK_BYTES):
        data.extend(chunk)
        if len(data) > limit:
            raise BadRequestError(f"Image is larger than {limit // (1024 * 1024)} MB")
    return bytes(data)


def validate_image(file: BinaryIO) -> tuple[bytes, ImageType]:
    """Return the file's bytes and its detected type, or raise a 400."""
    data = read_limited(file)
    if not data:
        raise BadRequestError("The file is empty")
    image_type = detect_image_type(data[:12])
    if image_type is None:
        raise BadRequestError("Only JPEG, PNG and WebP images are allowed")
    return data, image_type
