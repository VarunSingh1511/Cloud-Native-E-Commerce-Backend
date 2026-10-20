# Database Hardening (Week 9)

Week 8 got the app talking to Azure Database for PostgreSQL. Week 9 made that connection safer and proved the backups work.

| Area | Before (Week 8) | After (Week 9) |
| --- | --- | --- |
| Who the app connects as | `ecomadmin`, the **server admin** | **`ecom_app`**: owns only the app's tables; cannot create users or databases |
| TLS | `sslmode=require`: encrypted, but the server's identity was **not** checked | **`sslmode=verify-full`**: encrypted, **and** the certificate and hostname are verified |
| Admin password | Stored inside the app's `DATABASE_URL` | **Rotated to a random value that is stored nowhere** |
| Backups | 7-day retention, never tested | **Restore drill done**: data proven recoverable |
| Firewall | 31 rules = the web app's outbound IPs | Re-checked: still exact, no allow-all rule |

## 1. Least privilege: the `ecom_app` database user
**Why:** if the app were ever compromised, for example through SQL injection or a leaked `DATABASE_URL`, the attacker gets only the app's rights. As server admin they could have created users, read other databases, or changed server-wide settings.

[scripts/create_app_db_user.py](../scripts/create_app_db_user.py), run with an admin connection, does the following:
- **Creates `ecom_app`** with `LOGIN`, `NOSUPERUSER`, `NOCREATEDB` and `NOCREATEROLE`.
- **Grants `CONNECT` on the `ecom` database, and `USAGE` and `CREATE` on schema `public`.** Since PostgreSQL 15, `CREATE` is no longer granted to everyone, and migrations need it.
- **Transfers ownership of every table and enum type to `ecom_app`.** Only an object's owner may `ALTER` it, and the app runs the migrations at startup. Sequences behind `id` columns follow their table automatically.
- **Can be run again**, for example to rotate the password: on a re-run it only changes the password.

**Two PostgreSQL 16 details the script handles, both found by running it against Azure:**
- Azure's server admin is **not a superuser**. A non-superuser must first be *granted membership* in a role it created (`GRANT ecom_app TO CURRENT_USER`) before it can hand tables over to that role.
- A non-superuser may not run any `ALTER ROLE` that even *mentions* `SUPERUSER`. The first version did that on re-runs and failed on Azure with "permission denied to alter role". A test now runs the script **as a non-superuser admin**, so this can't come back.

**Verified:**
- Locally: `ecom_app` can run migrations (downgrade and upgrade) on its tables. `CREATE ROLE`, `CREATE DATABASE` and reading `pg_authid` are all **refused** ("permission denied").
- On Azure:
  - **migration 4 ran at startup as `ecom_app`**, and `products` is owned by `ecom_app`
  - `pg_stat_activity` shows the live app's connection as `user=ecom_app ssl=True TLSv1.3`, with **no** connection as `ecomadmin`

**Break-glass admin access:** the admin password was rotated to 40 random characters and **not stored anywhere**. If admin access is ever needed:

```bash
az postgres flexible-server update -g rg-ecom-mini -n <server> --admin-password <new-password>
```

Also add a temporary firewall rule for your IP, and remove it when done.

## 2. Verified TLS (`verify-full`)
| `sslmode` | Encrypted? | Checks the server is really Azure? |
| --- | --- | --- |
| `require` (Week 8) | Yes | **No.** An attacker in the middle could present any certificate. |
| **`verify-full`** (Week 9) | Yes | **Yes.** The certificate must be signed by a trusted root CA *and* match the hostname. |

The app's `DATABASE_URL` now ends in:

```text
?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt
```

**Why name the certificate file instead of `sslrootcert=system`:**
- `psycopg[binary]` ships its **own** copy of libpq and OpenSSL.
- `system` makes that bundled OpenSSL look in *its* built-in certificate folder, which doesn't exist in the Debian image. The result was "certificate verify failed".
- Pointing at Debian's CA bundle, which contains **DigiCert Global Root G2** and **Microsoft RSA Root CA 2017** (the roots Azure PostgreSQL uses), works.

**Verified:**
- the connection is TLS 1.3, and the certificate is verified
- **a negative test:** connecting with the server's **IP address** instead of its hostname is **refused** ("does not match host name"), which proves the hostname check really runs

## 3. Backup and restore drill
Azure takes automatic backups: **7-day retention**, locally redundant (geo-backup is off to stay in the free tier). A backup you have never restored is only a hope, so the drill was:
1. `az postgres flexible-server restore --source-server <server> --restore-time <a few minutes ago> --name <server>-restore`. This creates a **new** server from the backup; the original is untouched.
2. Connect to the restored server and check the data.
3. **Delete the restored server.**

**Results (2026-10-20):**

| Step | Result |
| --- | --- |
| Restore point | 09:55:37 UTC on 2026-10-20 (7-day retention; the earliest restore point was the previous evening) |
| `restore` command | **431 seconds (about 7 minutes)** until the new server was `Ready` |
| Restored server | Same settings as the source: B1ms, v16, 32 GB, Malaysia West. **All firewall rules were copied too.** |
| Data check (as `ecom_app`, TLS 1.3, `verify-full`) | The owner's **admin account** was present (plus 2 test customers that existed at that moment). Alembic was at `9b475d3a1915`. |
| Point-in-time accuracy | Correct: migration 4 (`image_url`) was deployed **after** 09:55:37, and the restored copy did **not** have that column. A restore gives you the database exactly as it was at the chosen moment. |
| Clean-up | Restored server deleted. **It existed for 10 minutes** (09:59–10:09 UTC). |

In a real incident you would:
1. restore to just before the problem
2. check the data
3. point the app's `DATABASE_URL` at the restored server (or copy the needed rows back)

The original server is never modified by a restore.

**Cost:** the restored server ran for 10 minutes. That fits within the free 750 hours a month (one server running all month uses at most 744 hours).

## 4. Firewall
- Re-checked: the 31 `app-outbound-N` rules **exactly match** the web app's `possibleOutboundIpAddresses`, and there is **no** `0.0.0.0` ("allow all Azure services") rule.
- **If the app's outbound IPs ever change** (for example after moving to a different plan tier), compare the two lists and add or remove rules:

  ```bash
  az webapp show -g rg-ecom-mini -n <app> --query possibleOutboundIpAddresses -o tsv
  az postgres flexible-server firewall-rule list -g rg-ecom-mini --server-name <server> -o table
  ```

  Terraform (Week 10) will keep the two lists in sync automatically.
- **Temporary rules for your PC** (named `temp-*`) are only for admin tasks and must be deleted right after.

## Not done (and why)
- **Private networking** (a VNet with a private endpoint) is the real fix for "public endpoint plus IP allow-list", but the **F1 tier cannot join a VNet**.
- **Entra ID (passwordless) login to PostgreSQL** would remove the database password entirely. It's a good next step; it was skipped to keep the project simple.
- **Azure Key Vault** for the connection string. For now App Service settings (encrypted at rest) hold it. Key Vault would add rotation and auditing.
