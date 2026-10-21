"""Fill a running deployment with the DRIPPY demo catalogue, through the public API.

Usage:
    python scripts/seed_demo.py https://<app-name>.azurewebsites.net admin@example.com
    python scripts/seed_demo.py http://localhost:8000 admin@example.com

It asks for the admin password (hidden, never stored), then creates three
categories and six garments in sizes S, M and L (one product per size, named
"<garment> - <size>", each with its own stock), and uploads each garment's photo
from scripts/demo_images/ to Blob Storage. Running it again skips what exists.
Only the Python standard library is used.
"""

import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

IMAGES = Path(__file__).resolve().parent / "demo_images"
SIZES = ("S", "M", "L")

CATEGORIES = ("Tops", "Outerwear", "Bottoms")

# Stock per size is deliberately uneven, so the shop shows "Only N left" and "Sold out".
CATALOGUE: list[dict[str, Any]] = [
    {"name": "Essential Tee", "category": "Tops", "price": 999, "image": "essential-tee.jpg",
     "description": "Heavyweight cotton tee with a boxy fit and a small chest logo.",
     "stock": {"S": 8, "M": 12, "L": 10}},
    {"name": "Heavyweight Hoodie", "category": "Tops", "price": 2499, "image": "heavyweight-hoodie.jpg",
     "description": "450 gsm brushed fleece, kangaroo pocket, double-lined hood.",
     "stock": {"S": 0, "M": 2, "L": 6}},
    {"name": "Crewneck Sweatshirt", "category": "Tops", "price": 1999, "image": "crewneck-sweatshirt.jpg",
     "description": "Raglan-sleeve crewneck in washed sage with a ribbed hem.",
     "stock": {"S": 6, "M": 7, "L": 5}},
    {"name": "Track Jacket", "category": "Outerwear", "price": 3299, "image": "track-jacket.jpg",
     "description": "Retro full-zip track top with contrast sleeve stripes.",
     "stock": {"S": 4, "M": 5, "L": 0}},
    {"name": "Varsity Bomber", "category": "Outerwear", "price": 4499, "image": "varsity-bomber.jpg",
     "description": "Wool-blend body, cream sleeves, striped rib trims and a chenille patch.",
     "stock": {"S": 3, "M": 1, "L": 2}},
    {"name": "Cargo Pants", "category": "Bottoms", "price": 2799, "image": "cargo-pants.jpg",
     "description": "Relaxed straight-leg cargos in khaki twill with flap pockets.",
     "stock": {"S": 5, "M": 9, "L": 7}},
]

TIMEOUT_SECONDS = 60  # the free App Service tier may need a cold start


class SeedError(Exception):
    """An API call failed in a way the script cannot recover from."""


def request(base_url: str, method: str, path: str, token: str | None = None,
            json_body: Any = None, form: dict[str, str] | None = None,
            multipart: tuple[bytes, str] | None = None) -> tuple[int, Any]:
    """Send one request and return (status code, parsed JSON body or None)."""
    headers: dict[str, str] = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode()
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(form).encode()
    elif multipart is not None:
        data, headers["Content-Type"] = multipart
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read()
        try:
            return error.code, json.loads(body) if body else None
        except json.JSONDecodeError:
            return error.code, None


def multipart_file(field: str, filename: str, content: bytes, content_type: str) -> tuple[bytes, str]:
    """Encode one file as multipart/form-data (what the image upload endpoint expects)."""
    boundary = uuid.uuid4().hex
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n").encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    return head + content + tail, f"multipart/form-data; boundary={boundary}"


def expect(status: int, body: Any, *ok: int) -> Any:
    if status not in ok:
        detail = body.get("detail") if isinstance(body, dict) else body
        raise SeedError(f"API answered {status}: {detail}")
    return body


def seed(base_url: str, email: str, password: str) -> None:
    base_url = base_url.rstrip("/")
    status, body = request(base_url, "POST", "/auth/login", form={"username": email, "password": password})
    token = expect(status, body, 200)["access_token"]

    categories = {c["name"]: c["id"] for c in expect(*request(base_url, "GET", "/categories"), 200)}
    for name in CATEGORIES:
        if name not in categories:
            created = expect(*request(base_url, "POST", "/categories", token, json_body={"name": name}), 201)
            categories[name] = created["id"]
            print(f"created category {name}")

    existing = {p["name"]: p for p in expect(*request(base_url, "GET", "/products?limit=100"), 200)}
    storage_available = True
    for garment in CATALOGUE:
        image = (IMAGES / garment["image"]).read_bytes()
        for size in SIZES:
            name = f"{garment['name']} - {size}"
            product = existing.get(name)
            if product is None:
                product = expect(*request(base_url, "POST", "/products", token, json_body={
                    "name": name, "price": garment["price"], "description": garment["description"],
                    "category_id": categories[garment["category"]]}), 201)
                expect(*request(base_url, "PUT", f"/inventory/{product['id']}", token,
                                json_body={"quantity": garment["stock"][size]}), 200)
                print(f"created {name} (stock {garment['stock'][size]})")
            else:
                print(f"exists  {name}")
            if storage_available and not product.get("image_url"):
                status, body = request(base_url, "POST", f"/products/{product['id']}/image", token,
                                       multipart=multipart_file("file", garment["image"], image, "image/jpeg"))
                if status == 503:  # no Blob Storage configured (e.g. local Compose): keep going without photos
                    storage_available = False
                    print("image storage not configured here: products are created without photos")
                else:
                    expect(status, body, 200)
                    print(f"        uploaded photo for {name}")
    print(f"done: {len(CATALOGUE)} garments x {len(SIZES)} sizes. Open {base_url}/shop/")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    password = getpass.getpass(f"Admin password for {argv[2]}: ")
    try:
        seed(argv[1], argv[2], password)
    except (SeedError, urllib.error.URLError) as error:
        print(f"Seeding stopped: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
