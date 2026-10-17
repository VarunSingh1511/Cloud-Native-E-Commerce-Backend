# Checkout: One Transaction, All or Nothing

Placing an order changes four things: it **creates an order**, **adds order items**, **reduces stock** and **empties the cart**. These must happen together or not at all.
- An order without the stock reduction would oversell.
- A stock reduction without an order would lose stock.

That is what a database **transaction** guarantees. The code is in `app/services/orders.py` (`checkout` and `_place_order`).

## The steps

```text
POST /orders
  │
  ├─ cart empty? ──────────────────────────────► 400 "Cart is empty"   (nothing changed)
  │
  │  BEGIN (one transaction)
  ├─ 1. SELECT inventory ... FOR UPDATE           lock the stock rows of every cart product,
  │                                               in product_id order
  ├─ 2. check every line: requested <= stock?
  │        no ──► ROLLBACK ────────────────────► 409 "Not enough stock for 'X'
  │                                                    (requested 3, available 1)"
  ├─ 3. INSERT order + order_items                copy product name and current price
  ├─ 4. UPDATE inventory: quantity -= requested
  ├─ 5. DELETE cart_items                         empty the cart
  │  COMMIT ───────────────────────────────────► 201 order
  │
  └─ any error in 1-5 ──► ROLLBACK ─────────────► error; nothing changed
```

In code, the whole thing is wrapped like this:

```python
try:
    order = _place_order(db, cart)   # steps 1-5, nothing is permanent yet
    db.commit()                      # everything becomes permanent at once
except Exception:
    db.rollback()                    # undo every step, release the locks
    raise
```

## Why each part matters

**`SELECT ... FOR UPDATE` (row locking).** Here is what happens without a lock:
1. Two customers check out the last unit at the same time.
2. Both read `quantity = 1`, and both pass the check.
3. Both reduce the stock, so the product is oversold.

`FOR UPDATE` locks the stock rows until this transaction ends. The second checkout **waits** at step 1, then reads the updated `quantity = 0` and gets 409.

This was verified against the real database with two simultaneous checkouts for the last unit:
- one order was placed
- the other waited for the lock (about 1 second, the time the first checkout held it) and then got 409
- the final stock was 0

**Locking in `product_id` order.** Suppose customer A locks the mouse, then wants the keyboard, while customer B has locked the keyboard and wants the mouse. Each waits for the other forever: a *deadlock*. If everyone locks rows in the same order (lowest product ID first), that cycle cannot form.

**Checking every line before writing anything.** If one product is short, we stop before any row has changed.

**One commit at the end.** Nothing is visible to other requests until `COMMIT`. If the server crashed halfway, PostgreSQL would discard the unfinished transaction automatically.

**`db.rollback()` on any error.** This covers more than "not enough stock". A bug or a database error at any step also undoes everything. `test_failure_mid_checkout_rolls_back_everything` proves this: it forces a crash *after* the order rows were inserted, then checks that there is no order, the stock is untouched and the cart is still full. Removing the `db.rollback()` line makes that test fail.

**The `CHECK (quantity >= 0)` constraint.** It is the last line of defence. Even if the application logic had a bug, PostgreSQL would refuse to store negative stock, and the transaction would roll back.

## Prices and money
- **The cart shows current prices.** The order **copies** each product's name and price at checkout (`order_items.product_name`, `order_items.unit_price`), so later price changes or product deletions never alter what a customer bought.
- **Totals are calculated with Python's `Decimal`**, using the exact `NUMERIC` values from PostgreSQL, and only converted to JSON numbers in the response. With floats, `4.35 × 100` is `434.99999999999994`; with `Decimal` it is exactly `435.00`.
- **Stock is reserved at checkout, not when adding to the cart.** Only the check inside the locked transaction is reliable.

## Cancelling an order (admin)
`PATCH /orders/{id}/status` follows `ALLOWED_STATUS_CHANGES`:

```text
PLACED ──► SHIPPED ──► DELIVERED
   │
   └─────► CANCELLED        (any other change: 409)
```

Cancelling **returns the quantities to stock** in the same transaction as the status change. The order row is locked first (`with_for_update=True`), so two admins cancelling at the same moment cannot restock twice. Lines whose product has since been deleted are skipped.

## Who can see what
- Customers see only their own cart and orders.
- Opening another customer's order returns **404, not 403**, so nobody can probe which order IDs exist.
- Admins see all orders.

## Tests
| File | Covers |
| --- | --- |
| `tests/test_checkout.py` | Success, stock reduced, cart emptied, last units, price snapshot, deleted product keeps history, empty cart (400), insufficient stock (409, with nothing changed), forced mid-checkout failure rolls back |
| `tests/test_orders.py` | Own orders only, 404 for other customers' orders, admin sees all |
| `tests/test_order_status.py` | Every allowed and blocked status change, cancel restocks, no double restock, admin only |
| `tests/test_end_to_end.py` | register → login → browse → cart → checkout → order → database check |

**Not covered by automated tests:** two checkouts at the same moment. The test setup runs every request on one database connection, so real concurrency cannot happen there. It was verified once by hand against the real database (see above).
