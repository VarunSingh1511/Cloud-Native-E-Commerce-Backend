# Testing (Week 12 final check)

**196 automated tests**, run on every pull request (see [cicd.md](cicd.md)). Run them locally with `pytest`; it needs the `ecom-db` container.

## How the tests work
- **Real PostgreSQL, not a stand-in.** `tests/conftest.py` points the app at the separate `ecom_test` database and applies the real Alembic migrations once per run. Constraints, enums and migrations are therefore tested exactly as they run in production.
- **Every test is rolled back.** Each test runs inside an outer transaction that is undone afterwards, so tests are independent and the database stays empty.
- **One fixture per kind of caller:** `client` (anonymous), `customer_client` and `admin_client`.
- **Azure is never contacted.** Blob Storage is replaced by `FakeImageStorage` and telemetry by a recorder, so the tests run offline and in CI.

## Endpoint coverage matrix

✓ means at least one test asserts that response. "–" means the response cannot happen for that endpoint.

| Endpoint | Success | 400 | 401 | 403 | 404 | 409 | 422 | Other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET /` | ✓ | – | – | – | – | – | – | |
| `GET /health` | ✓ | – | – | – | – | – | – | works with the database down |
| `GET /health/ready` | ✓ | – | – | – | – | – | – | 503 with the database down |
| `POST /auth/register` | ✓ | – | – | – | – | ✓ duplicate (any case) | ✓ email, password | role field ignored; hash stored |
| `POST /auth/login` | ✓ | – | ✓ wrong password, unknown email | – | – | – | ✓ missing fields | case-insensitive email |
| `GET /users/me` | ✓ | – | ✓ none, invalid, expired, deleted user | – | – | – | – | |
| `GET /products` | ✓ paging, filter, search | – | – | – | – | – | ✓ paging values | `%` searched literally |
| `GET /products/{id}` | ✓ | – | – | – | ✓ | – | ✓ non-integer ID | |
| `POST /products` | ✓ | ✓ unknown category | ✓ | ✓ | – | – | ✓ invalid, missing, too large | |
| `PUT /products/{id}` | ✓ | ✓ unknown category | ✓ | ✓ | ✓ | – | ✓ | |
| `DELETE /products/{id}` | ✓ | – | ✓ | ✓ | ✓ | – | – | removes stock and image; order history kept |
| `POST /products/{id}/image` | ✓ | ✓ fake or oversized file | ✓ | ✓ | ✓ | – | ✓ missing file | 503 without storage; failed save deletes the upload |
| `GET /categories` | ✓ sorted | – | – | – | – | – | – | |
| `GET /categories/{id}` | ✓ | – | – | – | ✓ | – | – | |
| `POST /categories` | ✓ | – | ✓ | ✓ | – | ✓ duplicate | ✓ blank, too long | |
| `GET /inventory/{product_id}` | ✓ | – | – | – | ✓ | – | – | |
| `PUT /inventory/{product_id}` | ✓ | – | ✓ | ✓ | ✓ | – | ✓ negative, missing | |
| `GET /cart` | ✓ | – | ✓ | – | – | – | – | current prices, exact decimal total |
| `POST /cart/items` | ✓ | ✓ unknown product | ✓ | – | – | – | ✓ quantity | repeat adds merge |
| `DELETE /cart/items/{id}` | ✓ | – | ✓ | – | ✓ incl. another user's item | – | – | |
| `POST /orders` (checkout) | ✓ | ✓ empty cart | ✓ | – | – | ✓ not enough stock | – | rollback on failure; **concurrent last unit** |
| `GET /orders` | ✓ newest first; admin sees all | – | ✓ | – | – | – | – | |
| `GET /orders/{id}` | ✓ | – | ✓ | – | ✓ incl. another customer's order | – | – | |
| `PATCH /orders/{id}/status` | ✓ ship, deliver, cancel | – | ✓ | ✓ | ✓ | ✓ blocked change | ✓ unknown status | cancel restocks once |
| `POST /diagnostics/error` | 500 (by design) | – | ✓ | ✓ | – | – | – | no stack trace in the response |

**Beyond the endpoints:**
- **Security:** password hashing, and tokens that are tampered with, expired, signed with another key or use `alg=none`.
- **Configuration:** a short `SECRET_KEY` refuses to start; a shared `.env` is accepted.
- **Database constraints:** tested directly against the database.
- **Scripts:** the `start.py` start-up, `create_admin` and `create_app_db_user`.
- **Telemetry:** off by default; uses the Azure identity; attached to the app.
- **An end-to-end shopping test.**

## Tests that prove a failure is handled

| Test | What it proves | Mutation-checked |
| --- | --- | --- |
| `test_failure_mid_checkout_rolls_back_everything` | An error halfway through checkout leaves no order, no stock change and the cart intact. | Yes |
| `test_database_failure_removes_the_uploaded_file` | If saving the image URL fails, the uploaded blob is deleted (compensating action). | Yes |
| `test_two_buyers_cannot_both_get_the_last_unit` | Two real, concurrent checkouts for the last unit give exactly one order, one 409 and stock 0. | Yes: without the row lock both buyers "win" (a double sale) and the test fails |
| `test_role_change_applies_to_an_existing_token` | Promoting or demoting a user takes effect immediately, without a new token, because the role is read from the database on every request. | n/a |
| `test_telemetry_instruments_the_existing_app` | The Application Insights instrumentation is really attached to the app (Week 12 regression). | Yes |

*Mutation-checked* means the protection was removed on purpose, the test failed, and the code was restored. It shows the test really guards that line.

**The concurrency test** is the only one that commits to the test database. It needs two real connections, because row locks only work between separate transactions. It creates its own product and two customers, and its fixture deletes them again even if the test fails. It passed 10 runs in a row.

## After every deployment
`scripts/smoke_test.py` runs 10 live checks: health, readiness, docs, product list, register, login, current user, anonymous write → 401, customer write → 403, and HTTP → HTTPS redirect. GitHub Actions runs it after each deploy and rollback.

## Known gaps (accepted)
- **Admin flows on the live system** (creating products, uploading an image, shipping an order) are checked by hand, not by the smoke test, because that would need an admin password in CI. They're part of the demo rehearsal ([demo-script.md](demo-script.md)).
- **The `httpx` deprecation warning from Starlette's test client.** Fixing it means a new library (`httpx2`), so it was left alone.
- **No coverage percentage is measured.** That would need a new library, and the matrix above answers the more useful question: which responses are tested.
