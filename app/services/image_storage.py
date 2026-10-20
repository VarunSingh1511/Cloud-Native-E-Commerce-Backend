"""Where product images are kept: Azure Blob Storage.

Routers and services depend on the small `ImageStorage` interface, not on Azure
directly. That keeps Azure code in one place and lets tests replace the real
storage with a fake (through FastAPI's dependency_overrides, like get_db).
"""

from functools import lru_cache
from typing import Protocol

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError

# Every upload gets a new random name, so a URL's content never changes and
# browsers may cache it for a year.
_CACHE_FOREVER = "public, max-age=31536000, immutable"


class ImageStorage(Protocol):
    """What the app needs from an image store."""

    def upload(self, blob_name: str, data: bytes, content_type: str) -> str:
        """Store the bytes under `blob_name` and return the public URL."""
        ...

    def delete(self, url: str) -> None:
        """Delete the image at `url` (a URL previously returned by `upload`)."""
        ...


class AzureBlobImageStorage:
    """Stores images as blobs in one Azure Storage container.

    Authentication uses DefaultAzureCredential, never an account key:
    - on Azure App Service it uses the web app's managed identity;
    - on a developer PC it uses the `az login` session.
    """

    def __init__(self, account_url: str, container_name: str) -> None:
        service = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        self._container: ContainerClient = service.get_container_client(container_name)

    def upload(self, blob_name: str, data: bytes, content_type: str) -> str:
        blob = self._container.upload_blob(
            blob_name,
            data,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type, cache_control=_CACHE_FOREVER),
        )
        return blob.url

    def delete(self, url: str) -> None:
        prefix = self._container.url.rstrip("/") + "/"
        if url.startswith(prefix):  # ignore URLs that don't belong to this container
            self._container.delete_blob(url[len(prefix):])


@lru_cache
def _azure_storage(account_url: str, container_name: str) -> AzureBlobImageStorage:
    """Create the Azure client once and reuse it for every request."""
    return AzureBlobImageStorage(account_url, container_name)


def get_image_storage() -> ImageStorage:
    """FastAPI dependency: the configured image storage, or 503 if there is none."""
    if not settings.azure_storage_account_url:
        raise ServiceUnavailableError("Image storage is not configured")
    return _azure_storage(settings.azure_storage_account_url, settings.azure_storage_container)
