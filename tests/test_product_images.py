"""Tests for product images: POST /products/{id}/image and clean-up on delete.

Blob Storage is replaced by FakeImageStorage through FastAPI's dependency_overrides,
so these tests never touch Azure.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.services.image_storage import get_image_storage, get_optional_image_storage
from app.services.images import MAX_IMAGE_BYTES
from tests.helpers import create_product

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x40\x00\x00\x00WEBP" + b"\x00" * 64

FAKE_BASE_URL = "https://fake.blob.example/product-images/"


class FakeImageStorage:
    """In-memory stand-in for Azure Blob Storage."""

    def __init__(self) -> None:
        self.blobs: dict[str, tuple[bytes, str]] = {}
        self.fail_deletes = False

    def upload(self, blob_name: str, data: bytes, content_type: str) -> str:
        url = FAKE_BASE_URL + blob_name
        self.blobs[url] = (data, content_type)
        return url

    def delete(self, url: str) -> None:
        if self.fail_deletes:
            raise RuntimeError("storage is down")
        self.blobs.pop(url, None)


@pytest.fixture
def storage(use_test_session: None) -> Iterator[FakeImageStorage]:
    """Make every request use one fake storage for the length of the test."""
    fake = FakeImageStorage()
    app.dependency_overrides[get_image_storage] = lambda: fake
    app.dependency_overrides[get_optional_image_storage] = lambda: fake
    yield fake


def upload(client: TestClient, product_id: int, data: bytes, filename: str = "photo.png") -> object:
    return client.post(f"/products/{product_id}/image", files={"file": (filename, data)})


# --- Successful uploads ---


@pytest.mark.parametrize(
    ("data", "extension", "content_type"),
    [(PNG, "png", "image/png"), (JPEG, "jpg", "image/jpeg"), (WEBP, "webp", "image/webp")],
)
def test_upload_image(
    admin_client: TestClient,
    storage: FakeImageStorage,
    data: bytes,
    extension: str,
    content_type: str,
) -> None:
    product = create_product(admin_client)

    response = upload(admin_client, product["id"], data)

    assert response.status_code == 200
    url = response.json()["image_url"]
    assert url.startswith(f"{FAKE_BASE_URL}products/{product['id']}/")
    assert url.endswith(f".{extension}")
    assert storage.blobs[url] == (data, content_type)
    # The URL is saved on the product.
    assert admin_client.get(f"/products/{product['id']}").json()["image_url"] == url


def test_type_comes_from_content_not_filename(
    admin_client: TestClient, storage: FakeImageStorage
) -> None:
    product = create_product(admin_client)

    response = upload(admin_client, product["id"], JPEG, filename="misleading.png")

    assert response.json()["image_url"].endswith(".jpg")


def test_replacing_image_deletes_the_old_one(
    admin_client: TestClient, storage: FakeImageStorage
) -> None:
    product = create_product(admin_client)
    first = upload(admin_client, product["id"], PNG).json()["image_url"]

    second = upload(admin_client, product["id"], JPEG).json()["image_url"]

    assert second != first
    assert list(storage.blobs) == [second]


# --- Rejected uploads ---


@pytest.mark.parametrize(
    ("data", "filename", "message"),
    [
        (b"just some text", "notes.txt", "Only JPEG, PNG and WebP"),
        (b"<?php echo 'hi'; ?>", "photo.png", "Only JPEG, PNG and WebP"),
        (b"GIF89a" + b"\x00" * 20, "anim.gif", "Only JPEG, PNG and WebP"),
        (b"", "empty.png", "empty"),
        (PNG + b"\x00" * MAX_IMAGE_BYTES, "huge.png", "larger than 2 MB"),
    ],
    ids=["text", "fake-png", "gif", "empty", "too-large"],
)
def test_invalid_files_are_rejected(
    admin_client: TestClient,
    storage: FakeImageStorage,
    data: bytes,
    filename: str,
    message: str,
) -> None:
    product = create_product(admin_client)

    response = upload(admin_client, product["id"], data, filename)

    assert response.status_code == 400
    assert message in response.json()["detail"]
    assert storage.blobs == {}


def test_missing_file_field(admin_client: TestClient, storage: FakeImageStorage) -> None:
    product = create_product(admin_client)

    assert admin_client.post(f"/products/{product['id']}/image").status_code == 422


def test_unknown_product(admin_client: TestClient, storage: FakeImageStorage) -> None:
    response = upload(admin_client, 99999, PNG)

    assert response.status_code == 404
    assert storage.blobs == {}


def test_only_admins_can_upload(
    client: TestClient,
    customer_client: TestClient,
    admin_client: TestClient,
    storage: FakeImageStorage,
) -> None:
    product = create_product(admin_client)

    assert upload(client, product["id"], PNG).status_code == 401
    assert upload(customer_client, product["id"], PNG).status_code == 403
    assert storage.blobs == {}


def test_upload_without_configured_storage_is_503(admin_client: TestClient) -> None:
    # No `storage` fixture here, and tests don't set AZURE_STORAGE_ACCOUNT_URL.
    product = create_product(admin_client)

    response = upload(admin_client, product["id"], PNG)

    assert response.status_code == 503
    assert response.json()["detail"] == "Image storage is not configured"


# --- Clean-up ---


def test_deleting_product_deletes_its_image(
    admin_client: TestClient, storage: FakeImageStorage
) -> None:
    product = create_product(admin_client)
    upload(admin_client, product["id"], PNG)

    assert admin_client.delete(f"/products/{product['id']}").status_code == 200
    assert storage.blobs == {}


def test_storage_failure_does_not_block_product_delete(
    admin_client: TestClient, storage: FakeImageStorage
) -> None:
    product = create_product(admin_client)
    upload(admin_client, product["id"], PNG)
    storage.fail_deletes = True

    assert admin_client.delete(f"/products/{product['id']}").status_code == 200
    assert admin_client.get(f"/products/{product['id']}").status_code == 404


def test_product_delete_works_without_configured_storage(admin_client: TestClient) -> None:
    product = create_product(admin_client)

    assert admin_client.delete(f"/products/{product['id']}").status_code == 200


def test_database_failure_removes_the_uploaded_file(
    monkeypatch: pytest.MonkeyPatch,
    admin_client: TestClient,
    storage: FakeImageStorage,
    db_session: Session,
) -> None:
    """If saving the URL fails, the new file must not be left behind (compensating action)."""
    product = create_product(admin_client)

    def failing_commit() -> None:
        raise RuntimeError("database went away")

    monkeypatch.setattr(db_session, "commit", failing_commit)

    with pytest.raises(RuntimeError):
        upload(admin_client, product["id"], PNG)
    assert storage.blobs == {}
