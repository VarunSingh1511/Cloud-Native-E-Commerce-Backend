"""Unit tests for image validation (app/services/images.py)."""

import io

import pytest

from app.core.exceptions import BadRequestError
from app.services.images import (
    JPEG,
    MAX_IMAGE_BYTES,
    PNG,
    WEBP,
    detect_image_type,
    read_limited,
    validate_image,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 20
WEBP_BYTES = b"RIFF" + b"\x10\x00\x00\x00" + b"WEBP" + b"\x00" * 20


@pytest.mark.parametrize(
    ("data", "expected"), [(PNG_BYTES, PNG), (JPEG_BYTES, JPEG), (WEBP_BYTES, WEBP)]
)
def test_detects_allowed_types(data: bytes, expected: object) -> None:
    assert detect_image_type(data[:12]) == expected


@pytest.mark.parametrize(
    "data",
    [
        b"<script>alert(1)</script>",  # text pretending to be an image
        b"GIF89a" + b"\x00" * 10,  # a real image type we don't allow
        b"RIFF\x10\x00\x00\x00WAVE",  # RIFF container that isn't WebP
        b"\x89PN",  # truncated PNG signature
    ],
)
def test_rejects_other_content(data: bytes) -> None:
    assert detect_image_type(data[:12]) is None


def test_validate_returns_bytes_and_type() -> None:
    data, image_type = validate_image(io.BytesIO(PNG_BYTES))

    assert data == PNG_BYTES
    assert image_type == PNG


def test_validate_rejects_empty_file() -> None:
    with pytest.raises(BadRequestError, match="empty"):
        validate_image(io.BytesIO(b""))


def test_validate_rejects_non_image() -> None:
    with pytest.raises(BadRequestError, match="Only JPEG, PNG and WebP"):
        validate_image(io.BytesIO(b"just some text"))


def test_read_limited_accepts_exactly_the_limit() -> None:
    assert len(read_limited(io.BytesIO(b"x" * MAX_IMAGE_BYTES))) == MAX_IMAGE_BYTES


def test_read_limited_stops_early_on_oversized_file() -> None:
    oversized = io.BytesIO(PNG_BYTES + b"x" * (MAX_IMAGE_BYTES + 10))

    with pytest.raises(BadRequestError, match="larger than 2 MB"):
        read_limited(oversized)
    # It stopped reading soon after the limit instead of reading everything.
    assert oversized.tell() < MAX_IMAGE_BYTES + 128 * 1024
