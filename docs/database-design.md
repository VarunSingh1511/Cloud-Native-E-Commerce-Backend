# Database Design (draft, Week 2)

PostgreSQL 16, accessed through SQLAlchemy 2.0. The schema is created and changed only through Alembic migrations in `alembic/versions/`.

## Entity relationships

```text
categories 1 ──── 0..* products 1 ──── 0..1 inventory

users   (no relationships yet; carts and orders link to users in Week 5)
```

- One category has many products. A product has zero or one category.
- One product has zero or one inventory row (one-to-one).

## Tables

### `users`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `email` | varchar(255) | not null, unique index `ix_users_email` |
| `hashed_password` | varchar(255) | not null |
| `role` | enum `user_role` (`CUSTOMER`, `ADMIN`) | not null, default `CUSTOMER` (set by the app) |
| `created_at` | timestamptz | not null, default `now()` |

The table exists now so the schema is complete, but it is not used until authentication in Week 4. Only password hashes are stored, never plain passwords.

### `categories`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `name` | varchar(100) | not null, unique |

### `products`
| Column | Type | Constraints |
| --- | --- | --- |
| `id` | integer | primary key |
| `name` | varchar(100) | not null |
| `description` | varchar(500) | not null |
| `price` | numeric(10, 2) | not null |
| `category_id` | integer | nullable, foreign key → `categories.id`, `ON DELETE SET NULL`, indexed |
| `created_at` | timestamptz | not null, default `now()` |

### `inventory`
| Column | Type | Constraints |
| --- | --- | --- |
| `product_id` | integer | primary key **and** foreign key → `products.id`, `ON DELETE CASCADE` |
| `quantity` | integer | not null, default `0` |

## Design decisions

- **`NUMERIC(10, 2)` for prices.** Floating-point numbers cannot represent most decimal values exactly (`0.1 + 0.2 != 0.3`). `NUMERIC` stores exact amounts up to 99,999,999.99. The API still sends prices as JSON numbers.
- **Inventory is a separate table.** Stock changes often (every order), while product details rarely do. Keeping them apart means checkout only locks and updates small inventory rows. Using `product_id` as the primary key guarantees at most one stock row per product.
- **`ON DELETE SET NULL` for a product's category.** Deleting a category should not delete its products. They simply become uncategorised.
- **`ON DELETE CASCADE` for inventory.** A stock row has no meaning without its product, so it is removed with it.
- **Index on `products.category_id`.** PostgreSQL indexes primary keys and unique columns automatically, but not foreign keys. This index keeps "products in category X" queries fast.
- **Unique index on `users.email`.** It prevents duplicate accounts and speeds up the login lookup.
- **Named constraints.** A naming convention in `app/db/base.py` gives every constraint a predictable name (for example `fk_products_category_id_categories`), so later migrations can alter or drop them reliably.

## Planned changes
- **Week 3:** `CHECK` constraints (`price > 0`, `quantity >= 0`) added in a second migration; category and inventory endpoints.
- **Week 5:** `carts`, `cart_items`, `orders`, `order_items`. Order items store the price at purchase time.

## Testing approach
Tests use a separate `ecom_test` database. `alembic upgrade head` runs once per test run, so the migrations themselves are tested. Each test runs inside a transaction that is rolled back afterwards, so tests never see each other's data.
