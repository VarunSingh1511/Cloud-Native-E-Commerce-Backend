# DRIPPY: the demo shop (Week 12)

DRIPPY is a one-page clothing shop at **`/shop/`** on the same app, for example `https://<app>.azurewebsites.net/shop/`. It exists to show the backend working the way a customer would see it. It is plain HTML, CSS and JavaScript (`app/static/shop/`): no framework, no build step, no new library, and **no backend change**. It calls exactly the REST API the rest of this project documents.

## What a visitor can do
- **Browse** six garments, filtered by category (Tops, Outerwear, Bottoms).
- **Pick a size (S, M or L).** A size that is out of stock is crossed out; "Only N left" and "Sold out" badges come from the live stock levels.
- **Create an account or sign in** in a dialog. Pressing "Add to bag" while signed out asks you to sign in first, then adds the item.
- **The bag:** a slide-in drawer with photos, sizes, quantities (+ / Remove) and the total.
- **Checkout:** one click places the order in a single database transaction. If someone else bought the last unit first, the API's 409 message is shown.
- **My orders:** order history with status pills (Placed, Shipped, Delivered, Cancelled). Admins see all orders.
- **The footer** shows the live API version and a green dot from `/health/ready` ("database connected").

## How it uses the API

| Page feature | API call |
| --- | --- |
| Product grid, filters | `GET /products?limit=100`, `GET /categories`, `GET /inventory/{id}` per product (in parallel) |
| Sign up / sign in | `POST /auth/register`, `POST /auth/login`, `GET /users/me` |
| Bag | `GET /cart`, `POST /cart/items`, `DELETE /cart/items/{id}` |
| Checkout, My orders | `POST /orders`, `GET /orders` |
| Status dot | `GET /health/ready`, `GET /openapi.json` (version) |

**Sizes without a schema change.** Each size is an ordinary product named `<garment> - S`, `- M` or `- L`, with its own stock. The page groups the three into one card. Stock per size is realistic, and checkout, orders and the database are unchanged. Products without a size suffix show as one size ("OS").

**The bag is the server-side cart**, which is why adding requires signing in. The page also refuses to put more of a size in the bag than is in stock. The final check happens at checkout, under the row lock described in [checkout.md](checkout.md).

## Security
- **No HTML from data.** API data is written with `textContent` only, never `innerHTML`, so a product name like `<script>…` is shown as text, not run (XSS). A test fails if `app.js` ever contains `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` or `eval(`.
- **Content-Security-Policy:**
  - scripts, styles and API calls are allowed only from the site itself
  - images only from the site and `*.blob.core.windows.net`
  - no inline scripts: the HTML has none, and a test checks that
- **Images:** only `https://` or same-site URLs are used as image sources.
- **The login token** is kept in `sessionStorage`. It survives a page refresh and is removed when the tab closes or you sign out. An expired token (after 30 minutes) signs you out with a message.
- **Serving:** the shop is mounted under `/shop` *after* all API routes, so it can never hide one. A test checks that an encoded `../` cannot read files outside the shop folder.

## Demo data
`scripts/seed_demo.py` fills a deployment through the public API:
```bash
python scripts/seed_demo.py https://<app>.azurewebsites.net <your-admin-email>
```
- It asks for the admin password (hidden, never stored).
- It creates three categories and six garments × three sizes, with deliberately uneven stock (one size sold out, a few "only N left").
- It **uploads each photo to Azure Blob Storage** through `POST /products/{id}/image`, the Week 9 feature.
- Running it again skips what exists. Locally, without Blob Storage, it creates the products without photos and the cards show a placeholder.

The photos are in `scripts/demo_images/`. They were provided by the project owner for this demo and show the fictional DRIPPY brand only.

## Tested
- **Automated** (`tests/test_frontend.py`, 9 tests):
  - the page and its files are served
  - the strict CSP is present, and there are no inline scripts and no HTML-writing calls
  - the API and `/docs` are unaffected
  - path traversal returns 404
  - the seed catalogue is complete (S/M/L, images, a sold-out size and a low-stock size), and its multipart upload is well formed
- **In a real browser, before merging:** the whole flow was driven in headless Microsoft Edge against a local copy, with 17 checks:
  - rendering, the API status, a sold-out size disabled, the category filter
  - signed-out "add" opens sign-in, registration, and the pending item being added
  - two items in the bag with the right total (₹5,498), checkout succeeding, the bag emptying, stock going down
  - My orders, the stock limit with its message, and sign-out

  The layout was also checked at phone width (390 px).
