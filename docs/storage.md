# Product Images in Azure Blob Storage (Week 9)

Admins upload a product photo through the API. The file is stored in **Azure Blob Storage**, and its public URL is saved on the product (`products.image_url`). Clients show the image straight from Blob Storage; the API does not serve image bytes.

```text
Admin ──multipart upload──► POST /products/{id}/image  (App Service, admin token required)
                                 │ 1. validate: real JPEG/PNG/WebP, ≤ 2 MB
                                 │ 2. upload as products/<id>/<random-uuid>.<ext>   (managed identity, no keys)
                                 │ 3. save image_url in PostgreSQL, commit
                                 │ 4. delete the previous image (best effort)
                                 ▼
                     Storage account  stecommini<sfx>  (Malaysia West, Standard LRS, Hot)
                     └── container  product-images   (public read of single files, no listing)
                                 ▲
Browser / client ──GET image_url──┘   (no login; cached for a year)
```

## Endpoint
`POST /products/{product_id}/image`
- **Admin only:** 401 when not logged in, 403 for customers.
- **Body:** `multipart/form-data` with the file in a field called **`file`**. Swagger shows a file picker.
- **Returns:** the product, including `image_url`. Uploading again replaces the image.

| Status | When |
| --- | --- |
| 200 | Stored. `image_url` is the new public URL. |
| 400 | Not a JPEG, PNG or WebP image, empty, or larger than 2 MB |
| 404 | No such product |
| 422 | The `file` field is missing |
| 503 | Image storage is not configured (`AZURE_STORAGE_ACCOUNT_URL` unset) |

## Design decisions
- **The file type comes from the file's own bytes**, not from its name or the `Content-Type` header.
  - The client chooses both of those, so a script renamed `photo.png` would pass a name check.
  - [app/services/images.py](../app/services/images.py) checks the "magic number" at the start of the file: JPEG `FF D8 FF`, PNG `89 50 4E 47 0D 0A 1A 0A`, WebP `RIFF....WEBP`.
- **Size limit of 2 MB.** The file is read in 64 KB pieces, and reading stops as soon as it passes the limit.
- **A new random file name for every upload** (`products/<id>/<uuid>.<ext>`).
  - The content behind a URL never changes, so images are served with `Cache-Control: public, max-age=31536000, immutable`, and browsers never show a stale picture after a replace.
  - Random names also cannot be guessed. That doesn't matter for public product photos, but it's good practice.
- **Public-read container (owner's decision).**
  - Product photos are public anyway, so a permanent public URL is the simplest and fastest option, and image views cost the F1 app no CPU.
  - Access level `blob` means a file can be read only by its exact URL. **Listing the container is refused** (verified: 404).
  - Alternatives considered: private plus short-lived signed URLs (SAS), which is more code; or the API streaming every image, which would use up F1's CPU quota.
- **No storage keys anywhere.**
  - The storage account has **shared-key access disabled**, so account keys and connection strings do not work at all.
  - The app authenticates with `DefaultAzureCredential` ([app/services/image_storage.py](../app/services/image_storage.py)):
    - on App Service, that is the web app's **managed identity**
    - on a developer PC, it is the `az login` session
  - Both are granted **Storage Blob Data Contributor** on the **`product-images` container only**, not the whole account. This is least privilege.
- **Database and Blob Storage cannot share one transaction, so the order of steps matters.**
  1. Upload the new file.
  2. Save its URL and commit. **If the commit fails, the just-uploaded file is deleted** (a *compensating action*), so no orphaned file is left behind.
  3. Only then delete the old file.

  Deletes of old files are *best effort*: a failure is logged, but it never fails the request. The worst case is a leftover unused file, never a product pointing at a missing image.
- **Deleting a product deletes its image**, also best effort.
- **Interface plus dependency injection.** Routers depend on the small `ImageStorage` interface, through `get_image_storage()` / `get_optional_image_storage()`. That keeps all Azure code in one file and lets tests swap in a fake.

## Tests (no Azure needed)
- [tests/test_images.py](../tests/test_images.py): type detection, empty and oversized files, early stop when reading.
- [tests/test_product_images.py](../tests/test_product_images.py), which uses an in-memory `FakeImageStorage` through `app.dependency_overrides` (the "mocked storage client"):
  - JPEG, PNG and WebP uploads; the type is taken from the content, not the name; replacing an image deletes the old one
  - 400s (text, fake PNG, GIF, empty, too large); 404, 401, 403; 503 when storage isn't configured
  - deleting a product deletes its image; a storage outage does not block the delete
  - a database failure after upload removes the uploaded file. This test was mutation-checked: without the compensating delete, it fails.

## Verified live on Azure
1. A real 1×1 PNG uploaded through the HTTPS API returned a URL in the storage account.
2. That URL opened **without any login** (200, `image/png`, cache header set).
3. Replacing the image gave a new URL, and the old one returned **404** (deleted).
4. An anonymous container listing returned **404** (refused).
5. A text file named `.png` got **400**, and a customer got **403**.
6. Deleting the product turned its image URL into **404**.

## Local development
- **Tests** never need Azure.
- **`uvicorn` on your PC**:
  - Without `AZURE_STORAGE_ACCOUNT_URL` in `.env`, the upload endpoint answers 503 and everything else works.
  - With it set (to `https://<account>.blob.core.windows.net`) and `az login` done, local uploads go to the real Azure container, using your container role.
- **Docker Compose** containers have no Azure login, so uploads answer 503 there. That's expected.

## Azure resources
| Resource | Settings |
| --- | --- |
| Storage account `stecommini<sfx>` | Malaysia West (next to the app), Standard_LRS, StorageV2, Hot, HTTPS only, TLS 1.2+, shared keys **disabled**, blob public access allowed (used only by the container below) |
| Container `product-images` | Public access level `blob` |
| Role assignments | Web app identity and the owner: Storage Blob Data Contributor on the container |
| App settings | `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_STORAGE_CONTAINER=product-images` |

**Cost:** ₹0 within the student free amount (5 GB hot LRS, 20,000 reads and 10,000 writes a month). Beyond that, about ₹1.7 per GB per month.
