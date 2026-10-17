# Database Design

PostgreSQL 16, accessed through SQLAlchemy 2.0. The schema is created and changed only through Alembic migrations in `alembic/versions/`.

| Migration | Week | What it does |
| --- | --- | --- |
| `fadf75fe9183` | 2 | Creates `users`, `categories`, `products`, `inventory` |
| `22d1fd6d142c` | 3 | Adds `CHECK` constraints; backfills missing inventory rows |
| `9b475d3a1915` | 5 | Creates `carts`, `cart_items`, `orders`, `order_items` and the `order_status` enum |

## Entity relationships

```text
categories 1 ──── 0..* products 1 ──── 1 inventory
                         │  │
                         │  └── 0..* order_items *──── 1 orders *──── 1 users
                         │                                              │
                         └───── 0..* cart_items *──── 1 carts 0..1 ─────┘
```

- One category has many products. A product has zero or one category.
- Every product has exactly one inventory row. The app creates it together with the product, and the Week 3 migration backfilled older products.
- Each user has at most one cart and any number of orders.
- Order items point to a product while it exists. If the product is deleted, they keep their own copy of its name and price.

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

### `carts`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `user_id` | integer | not null, **unique** (one cart per user), foreign key → `users.id`, `ON DELETE CASCADE` |
| `created_at` | timestamptz | not null, default `now()` |

### `cart_items`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `cart_id` | integer | not null, foreign key → `carts.id`, `ON DELETE CASCADE` |
| `product_id` | integer | not null, foreign key → `products.id`, `ON DELETE CASCADE`, indexed |
| `quantity` | integer | not null, `CHECK (quantity > 0)` |

There is also `UNIQUE (cart_id, product_id)` (`uq_cart_items_cart_id_product_id`): a product appears once per cart, and adding it again increases the quantity.

### `orders`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `user_id` | integer | not null, foreign key → `users.id` (no `ON DELETE` rule, so a user with orders cannot be deleted), indexed |
| `status` | enum `order_status` (`PLACED`, `SHIPPED`, `DELIVERED`, `CANCELLED`) | not null, default `PLACED` (set by the app) |
| `total_amount` | numeric(12, 2) | not null, `CHECK (total_amount >= 0)` |
| `created_at` | timestamptz | not null, default `now()` |

### `order_items`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `order_id` | integer | not null, foreign key → `orders.id`, `ON DELETE CASCADE`, indexed |
| `product_id` | integer | **nullable**, foreign key → `products.id`, `ON DELETE SET NULL`, indexed |
| `product_name` | varchar(100) | not null, a copy taken at checkout |
| `unit_price` | numeric(10, 2) | not null, `CHECK (unit_price > 0)`, the price paid, copied at checkout |
| `quantity` | integer | not null, `CHECK (quantity > 0)` |

## Design decisions

- **`NUMERIC(10, 2)` for prices.** Floating-point numbers cannot represent most decimal values exactly (`0.1 + 0.2 != 0.3`). `NUMERIC` stores exact amounts up to 99,999,999.99. The API still sends prices as JSON numbers and rejects anything above that maximum with 422.
- **Validation in two layers.**
  - Pydantic rejects bad input with a clear 422 before the database is touched.
  - `CHECK` constraints make PostgreSQL enforce the same rules for any data that bypasses the API, such as scripts, manual SQL or future bugs.
  - Alembic autogenerate includes `CHECK` constraints when it creates a **new** table, as in the Week 5 migration. It does not detect a `CHECK` **added to an existing** table, so the Week 3 migration was written by hand.
- **Inventory is a separate table.** Stock changes often (every order), while product details rarely do. Keeping them apart means checkout only locks and updates small inventory rows. Using `product_id` as the primary key guarantees at most one stock row per product.
- **The stock row is created with the product.** Both rows are inserted in the same transaction, so a product can never exist without stock information, and Week 5 checkout can always lock that row.
- **`ON DELETE SET NULL` for a product's category.** Deleting a category should not delete its products. They simply become uncategorised.
- **`ON DELETE CASCADE` for inventory.** A stock row has no meaning without its product, so it is removed with it.
- **Index on `products.category_id`.** PostgreSQL indexes primary keys and unique columns automatically, but not foreign keys. This index keeps "products in category X" queries fast, which is the `?category_id=` filter on `GET /products`.
- **Duplicate names are detected by the database.** Creating a category catches the unique constraint's error and returns 409. Checking with a SELECT first would not be safe if two requests create the same name at the same moment.
- **Unique index on `users.email`.** It prevents duplicate accounts and speeds up the login lookup. A duplicate registration is caught from this index and returns 409, the same pattern as category names.
- **Named constraints.**
  - A naming convention in `app/db/base.py` gives every constraint a predictable name, for example `fk_products_category_id_categories`, so later migrations can alter or drop them reliably.
  - Unique constraints include every column in their name, for example `uq_cart_items_cart_id_product_id`.
- **Order items copy the product name and price.** This is how the Week 3 open question was decided.
  - Deleting a product sets `order_items.product_id` to NULL (`ON DELETE SET NULL`), while the copied `product_name` and `unit_price` keep the order history complete.
  - The alternative, blocking the deletion of any product that was ever ordered, would have stopped admins from removing old products.
- **Deleting a product removes it from carts** (`ON DELETE CASCADE` on `cart_items.product_id`). A cart line has no meaning without its product, unlike an order line, which records a past purchase.
- **Users with orders cannot be deleted.** `orders.user_id` has no `ON DELETE` rule, so PostgreSQL rejects the delete. Order history must never silently disappear.
- **Indexes on foreign keys used in lookups:**
  - `orders.user_id`, for "my orders"
  - `order_items.order_id`, for loading an order's lines
  - `cart_items.product_id` and `order_items.product_id`, so deleting a product can quickly find the rows to cascade or set to NULL
  - The cart's `UNIQUE (cart_id, product_id)` index already serves lookups by `cart_id`.
- **Totals use `NUMERIC(12, 2)`**, which is larger than the `NUMERIC(10, 2)` used for single prices, because one order can contain several expensive items.

How checkout uses these tables in one transaction (row locking, rollback) is explained in `docs/checkout.md`.

## Testing approach
Tests use a separate `ecom_test` database.
- `alembic upgrade head` runs once per test run, so the migrations themselves are tested.
- Each test runs inside a transaction that is rolled back afterwards, so tests never see each other's data.
- `tests/test_constraints.py` inserts invalid rows directly, bypassing the API, to prove that PostgreSQL rejects them. It also checks that deleting a product keeps order history and removes cart lines.
