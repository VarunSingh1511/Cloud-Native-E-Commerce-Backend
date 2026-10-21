"""Tests for the DRIPPY demo shop (static files under /shop) and its seed catalogue."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "app" / "static" / "shop"


def load_seed_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_demo", ROOT / "scripts" / "seed_demo.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shop_page_is_served(client: TestClient) -> None:
    response = client.get("/shop/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "DRIPPY" in response.text


@pytest.mark.parametrize(("path", "content_type"), [
    ("/shop/app.js", "javascript"),
    ("/shop/styles.css", "text/css"),
])
def test_shop_assets_are_served(client: TestClient, path: str, content_type: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


def test_page_has_a_strict_content_security_policy() -> None:
    html = (SHOP / "index.html").read_text(encoding="utf-8")
    policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)

    assert policy is not None
    assert "script-src 'self'" in policy.group(1)
    assert "unsafe-inline" not in policy.group(1)
    # Every <script> loads a file; none carries code inline.
    assert re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) == []


def test_script_never_writes_html() -> None:
    # API data reaches the page through textContent only, so it cannot inject markup (XSS).
    script = (SHOP / "app.js").read_text(encoding="utf-8")

    for risky in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert risky not in script


def test_api_and_docs_are_unaffected_by_the_shop(client: TestClient) -> None:
    assert client.get("/products").headers["content-type"].startswith("application/json")
    assert client.get("/docs").status_code == 200
    assert client.get("/shop/missing.js").status_code == 404


def test_shop_cannot_serve_files_outside_its_folder(client: TestClient) -> None:
    # Path traversal: an encoded "../" must not reach the application's source code.
    response = client.get("/shop/%2e%2e/%2e%2e/main.py")

    assert response.status_code == 404
    assert "FastAPI application entry point" not in response.text


def test_seed_catalogue_is_complete() -> None:
    seed = load_seed_script()

    names = [g["name"] for g in seed.CATALOGUE]
    assert len(names) == len(set(names)) == 6
    for garment in seed.CATALOGUE:
        assert set(garment["stock"]) == set(seed.SIZES) == {"S", "M", "L"}
        assert garment["category"] in seed.CATEGORIES
        assert (seed.IMAGES / garment["image"]).is_file()
    # The demo needs at least one sold-out size and one "only a few left" size.
    levels = [n for g in seed.CATALOGUE for n in g["stock"].values()]
    assert 0 in levels
    assert any(0 < n <= 3 for n in levels)


def test_seed_multipart_upload_is_well_formed() -> None:
    seed = load_seed_script()

    body, content_type = seed.multipart_file("file", "tee.jpg", b"\xff\xd8\xffJPEG", "image/jpeg")

    boundary = content_type.split("boundary=")[1]
    assert content_type.startswith("multipart/form-data; boundary=")
    assert body.startswith(f"--{boundary}\r\n".encode())
    assert b'name="file"; filename="tee.jpg"' in body
    assert b"\xff\xd8\xffJPEG" in body
    assert body.endswith(f"\r\n--{boundary}--\r\n".encode())
