# Database Design

PostgreSQL 16, accessed through SQLAlchemy 2.0. The schema is created and changed only through Alembic migrations in `alembic/versions/`.

| Migration | Week | What it does |
| --- | --- | --- |
| `fadf75fe9183` | 2 | Creates `users`, `categories`, `products`, `inventory` |
| `22d1fd6d142c` | 3 | Adds `CHECK` constraints; backfills missing inventory rows |

## Entity relationships

```text
categories 1 ──── 0..* products 1 ──── 1 inventory

users   (no relationships yet; carts and orders link to users in Week 5)
```

- One category has many products. A product has zero or one category.
- Every product has exactly one inventory row. The app creates it together with the product, and the Week 3 migration backfilled older products.

## Tables

### `users`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `email` | varchar(255) | not null, unique index `ix_users_email` |
| `hashed_password` | varchar(255) | not null |
| `role` | enum `user_role` (`CUSTOMER`, `ADMIN`) | not null, default `CUSTOMER` (set by the app) |
| `created_at` | timestamptz | not null, default `now()` |

Used for login since Week 4 (see `docs/security.md`).
- Only Argon2 password hashes are stored, never plain passwords.
- Emails are saved in lowercase, so the unique index also blocks duplicates that differ only in letter case.
- No migration was needed for authentication, because this table already had every column.

### `categories`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `name` | varchar(100) | not null, unique (case-sensitive) |

### `products`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `name` | varchar(100) | not null |
| `description` | varchar(500) | not null |
| `price` | numeric(10, 2) | not null, `CHECK (price > 0)` (`ck_products_price_positive`) |
| `category_id` | integer | nullable, foreign key → `categories.id`, `ON DELETE SET NULL`, indexed |
| `created_at` | timestamptz | not null, default `now()` |

### `inventory`
| Column | Type | Constraints |
| --- | --- | --- |
| `product_id` | integer | primary key **and** foreign key → `products.id`, `ON DELETE CASCADE` |
| `quantity` | integer | not null, default `0`, `CHECK (quantity >= 0)` (`ck_inventory_quantity_non_negative`) |

## Design decisions

- **`NUMERIC(10, 2)` for prices.** Floating-point numbers cannot represent most decimal values exactly (`0.1 + 0.2 != 0.3`). `NUMERIC` stores exact amounts up to 99,999,999.99. The API still sends prices as JSON numbers and rejects anything above that maximum with 422.
- **Validation in two layers.**
  - Pydantic rejects bad input with a clear 422 before the database is touched.
  - `CHECK` constraints make PostgreSQL enforce the same rules for any data that bypasses the API, such as scripts, manual SQL or future bugs.
  - Alembic autogenerate does not detect `CHECK` constraints, so that migration was written by hand.
- **Inventory is a separate table.** Stock changes often (every order), while product details rarely do. Keeping them apart means checkout only locks and updates small inventory rows. Using `product_id` as the primary key guarantees at most one stock row per product.
- **The stock row is created with the product.** Both rows are inserted in the same transaction, so a product can never exist without stock information, and Week 5 checkout can always lock that row.
- **`ON DELETE SET NULL` for a product's category.** Deleting a category should not delete its products. They simply become uncategorised.
- **`ON DELETE CASCADE` for inventory.** A stock row has no meaning without its product, so it is removed with it.
- **Index on `products.category_id`.** PostgreSQL indexes primary keys and unique columns automatically, but not foreign keys. This index keeps "products in category X" queries fast, which is the `?category_id=` filter on `GET /products`.
- **Duplicate names are detected by the database.** Creating a category catches the unique constraint's error and returns 409. Checking with a SELECT first would not be safe if two requests create the same name at the same moment.
- **Unique index on `users.email`.** It prevents duplicate accounts and speeds up the login lookup. A duplicate registration is caught from this index and returns 409, the same pattern as category names.
- **Named constraints.** A naming convention in `app/db/base.py` gives every constraint a predictable name (for example `fk_products_category_id_categories`), so later migrations can alter or drop them reliably.

## Week 5 draft: cart and orders

This is a sketch to refine in Week 5 and is not implemented yet.

```text
users 1 ──── 0..1 carts 1 ──── 0..* cart_items *──── 1 products
users 1 ──── 0..* orders 1 ──── 1..* order_items *──── 1 products
```

| Table | Columns | Key constraints |
| --- | --- | --- |
| `carts` | `id`, `user_id`, `created_at` | `user_id` FK → `users`, **unique** (one cart per user), `ON DELETE CASCADE` |
| `cart_items` | `id`, `cart_id`, `product_id`, `quantity` | FKs to `carts` (CASCADE) and `products` (CASCADE); `UNIQUE (cart_id, product_id)` so adding the same product again increases the quantity; `CHECK (quantity > 0)` |
| `orders` | `id`, `user_id`, `status`, `total_amount`, `created_at` | `user_id` FK → `users`; `status` enum (e.g. `PLACED`, `CANCELLED`); `total_amount NUMERIC(12, 2)`, `CHECK (total_amount >= 0)` |
| `order_items` | `id`, `order_id`, `product_id`, `quantity`, `unit_price` | FK → `orders` (CASCADE); `CHECK (quantity > 0)`; **`unit_price` is copied at purchase time**, so later price changes do not alter past orders |

**Checkout in a single transaction** (`services/orders.py`):
1. Lock the cart's inventory rows with `SELECT ... FOR UPDATE`, so two checkouts cannot sell the same last unit.
2. If any quantity is too low, roll back and return 409.
3. Insert the order and its order items (with `unit_price`).
4. Reduce inventory.
5. Empty the cart.
6. Commit. Any error rolls everything back, so no partial order is ever saved.

**Open question for Week 5:** what happens to `order_items.product_id` when a product is deleted? There are two options:
- Block the deletion (`ON DELETE RESTRICT`, so the API returns 409).
- Keep the history by storing the product name on the order item and setting `product_id` to NULL.

## Testing approach
Tests use a separate `ecom_test` database.
- `alembic upgrade head` runs once per test run, so the migrations themselves are tested.
- Each test runs inside a transaction that is rolled back afterwards, so tests never see each other's data.
- `tests/test_constraints.py` inserts invalid rows directly, bypassing the API, to prove that PostgreSQL rejects them.
