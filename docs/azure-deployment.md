# Azure Deployment (Week 8)

The API runs on Azure as the **same Docker image** that runs locally with Docker Compose ("build once, run anywhere"). The image is stored in Azure Container Registry, run by Azure App Service on the free F1 tier, and connected to Azure Database for PostgreSQL.

> Resource names end in a random 4-character suffix because registry, server and web app names must be unique across all of Azure. The public URL is `https://<web-app-name>.azurewebsites.net`. It is deliberately not written in the repository, so bots don't use up the free tier's daily CPU quota.

## Architecture

```text
This PC: docker build ──► docker push ──► Azure Container Registry (Standard)       [India South Central]
                                              │  image: ecom-api:<git commit SHA>
                                              │  pulled with the web app's managed identity (AcrPull role, no password)
                                              ▼
Internet ──HTTPS──► App Service plan F1 (Linux) ─ web app runs the container           [Malaysia West]
                     settings → environment variables: DATABASE_URL, SECRET_KEY, ...
                          │                   │  TLS verify-full, user ecom_app, firewall: web app outbound IPs only
                          │                   ▼
                          │  Azure Database for PostgreSQL Flexible Server B1ms, v16    [Malaysia West]
                          │  managed identity (Storage Blob Data Contributor, container only)
                          ▼
                    Storage account (Standard LRS) / container product-images          [Malaysia West]
                    images are public-read by URL (no listing)   (Week 9, see docs/storage.md)
```

## Resources
All of these are in resource group `rg-ecom-mini` and tagged `project=ecom-mini`.

| Resource | Type / SKU | Region | Cost |
| --- | --- | --- | --- |
| `acrecommini<sfx>` | Container Registry, **Standard**, admin user disabled | India South Central | ₹0 under the student offer (1 Standard registry). Otherwise ₹64/day; the owner accepts this cost if it applies. |
| `asp-ecom-mini` | App Service plan, **F1 Free**, Linux | Malaysia West | ₹0 |
| `app-ecom-mini-<sfx>` | Web app running the container, system-assigned managed identity | Malaysia West | ₹0 (included in F1) |
| `psql-ecom-mini-my-<sfx>` | PostgreSQL Flexible **B1ms**, v16, 32 GB (auto-grow off), 7-day backups, no HA, no geo-backup | Malaysia West | ₹0 within 750 h/month |
| AcrPull role assignment | The web app's identity may pull from the registry | - | ₹0 |
| 31 firewall rules `app-outbound-N` | One per possible outbound IP of the web app | - | ₹0 |

### Why the app and database are in Malaysia West, not India
1. Week 7 chose India South Central, the only Indian region the student subscription policy allows.
2. Creating PostgreSQL B1ms there failed in **all three availability zones** with `RegionalAllocationFailed`: Azure had no capacity for that size.
3. The owner chose to move **both the web app and the database** to Malaysia West, another allowed region. **The app and its database must sit together**, because every request makes several database queries, and each one would otherwise cross countries.
4. The registry stayed in India. Images are only pulled when the app (re)starts, so the cross-region traffic is tiny.

## Key decisions
- **Container deploy, not code deploy.** The exact image tested locally is what runs in Azure. F1 accepted a custom container. Microsoft's docs were unclear on this, so it was confirmed by creating the app.
- **Image tags are git commit SHAs** (`ecom-api:08368f2`), never only `latest`. Every deployment can be traced to one commit, and a rollback just points the app at the previous tag.
- **No registry password.**
  - The registry's admin user is disabled.
  - The web app has a **system-assigned managed identity** (an Azure-managed identity tied to the app), which is granted only **AcrPull**, the right to download images.
  - On this PC, `az acr login` uses the owner's own Azure sign-in to push.
- **Migrations run at container start**, through the App Service *startup command* `python -m app.scripts.start`, which replaces the image's `CMD`. The script ([app/scripts/start.py](../app/scripts/start.py)) does two things:
  1. It runs `alembic upgrade head`. If the schema is already current, this does nothing.
  2. It calls `os.execvp` to **replace itself with uvicorn** (same process ID), so uvicorn is the main process and shuts down cleanly. Uvicorn runs with `--proxy-headers`, which makes it trust the `X-Forwarded-*` headers from Azure's front end, so the app knows the original request was **HTTPS**.

  This is safe because F1 runs one instance. The image's own `CMD` is unchanged, and Compose still uses its separate `migrate` service.
- **Why a Python script and not a shell one-liner (lesson learned).**
  - The first attempt used `sh -c "alembic upgrade head && exec uvicorn …"`. It worked with `docker run` locally, but **App Service splits the startup command on spaces and ignores quotes**.
  - The container therefore received `sh -c '"alembic' upgrade …`, failed with `Syntax error: Unterminated quoted string`, and exited with code 2.
  - App Service kept restarting it (43 stop requests). That used up F1's **60 CPU-minutes for the day**, and Azure paused the app with `QuotaExceeded` ("403 Site Disabled").
  - The fix is a startup command with no quotes at all. It was tested locally in the container first.
  - **Takeaways:**
    - Read the container log (`az webapp log download`) before guessing.
    - A crash-looping app on F1 burns its daily quota.
    - Startup commands and the image must stay compatible: images built before the start script existed cannot use this startup command, so they are not valid rollback targets.
- **The database firewall allows only the web app's outbound IPs.**
  - The "allow all Azure services" switch (rule `0.0.0.0`) is deliberately **not** used, because it would let any Azure customer's services reach the database login.
  - F1 cannot use private networking (VNet integration), so an IP allow-list is the strongest option on this tier.
  - The free tier shares a pool of outbound addresses, hence 31 rules.
- **TLS to the database** is enforced on both sides: `?sslmode=require` in `DATABASE_URL`, and `require_secure_transport=on` on the server.
- **Secrets never leave Azure.**
  - The database admin password and the production `SECRET_KEY` were generated randomly and written directly into the web app's *app settings*. They were never printed, saved to a file or committed, and they differ from the local development values.
  - App settings become environment variables inside the container, which `app/core/config.py` already reads, so **no code change was needed**.

## How settings reach the app
| App setting | Purpose |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://ecom_app:<password>@<server>.postgres.database.azure.com:5432/ecom?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt`. Since Week 9 this is the limited `ecom_app` user with verified TLS (see `docs/database-hardening.md`). |
| `SECRET_KEY` | Signs login tokens (a random 43-character value) |
| `ENVIRONMENT` | `production` (shown by `/health`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `WEBSITES_PORT` | `8000`: tells App Service which port the container listens on |
| `AZURE_STORAGE_ACCOUNT_URL` | `https://<storage-account>.blob.core.windows.net` (Week 9). Not a secret; access uses the managed identity. |
| `AZURE_STORAGE_CONTAINER` | `product-images` |

You can view or change these in the portal under *Web app → Settings → Environment variables*. Changing a setting restarts the app.

## Commands used
The Git Bash shell on Windows rewrites arguments that start with `/` (such as `/subscriptions/...`) into Windows paths. Run this first in Git Bash:

```bash
export MSYS_NO_PATHCONV=1
```

```bash
# 1. Registry and image (from a clean checkout of a commit)
az acr create -g rg-ecom-mini -n <acr> -l indiasouthcentral --sku Standard --admin-enabled false
docker build -t <acr>.azurecr.io/ecom-api:<sha> .
az acr login -n <acr>
docker push <acr>.azurecr.io/ecom-api:<sha>

# 2. App Service (F1 Linux) running the image, with a managed identity
az appservice plan create -g rg-ecom-mini -n asp-ecom-mini -l malaysiawest --sku F1 --is-linux
az webapp create -g rg-ecom-mini -p asp-ecom-mini -n <app> --container-image-name <acr>.azurecr.io/ecom-api:<sha> --assign-identity "[system]" --https-only true
az role assignment create --assignee-object-id <app-principal-id> --assignee-principal-type ServicePrincipal --role AcrPull --scope <acr-resource-id>
az webapp config set -g rg-ecom-mini -n <app> --ftps-state Disabled --min-tls-version 1.2 \
  --generic-configurations '{"acrUseManagedIdentityCreds": true, "healthCheckPath": "/health"}'
az webapp log config -g rg-ecom-mini -n <app> --docker-container-logging filesystem

# 3. PostgreSQL (B1ms, 32 GB, no auto-grow) + database
az postgres flexible-server create -g rg-ecom-mini -n <server> -l malaysiawest --tier Burstable --sku-name Standard_B1ms \
  --storage-size 32 --storage-auto-grow Disabled --version 16 --backup-retention 7 --geo-redundant-backup Disabled \
  --public-access None --admin-user ecomadmin --admin-password <generated>
az postgres flexible-server update -g rg-ecom-mini -n <server> --public-access Enabled     # endpoint on, but no rules yet
az postgres flexible-server db create -g rg-ecom-mini --server-name <server> --name ecom

# 4. Firewall: one rule per web-app outbound IP
az webapp show -g rg-ecom-mini -n <app> --query possibleOutboundIpAddresses -o tsv
az postgres flexible-server firewall-rule create -g rg-ecom-mini --server-name <server> --name app-outbound-1 --start-ip-address <ip> --end-ip-address <ip>

# 5. Settings and startup command
az webapp config appsettings set -g rg-ecom-mini -n <app> --output none --settings DATABASE_URL=... SECRET_KEY=... ENVIRONMENT=production ACCESS_TOKEN_EXPIRE_MINUTES=30 WEBSITES_PORT=8000
az webapp config set -g rg-ecom-mini -n <app> --startup-file "python -m app.scripts.start"
```

**CLI version notes (Azure CLI 2.90):**
- `flexible-server create` no longer accepts `--database-name` for normal servers, so the database is created with `db create --name`.
- Firewall rules take `--server-name` for the server and `--name` for the rule.
- `--public-access None` turns public access *off*, so it has to be enabled afterwards.

## Deploying a new version
```bash
SHA=$(git rev-parse --short=7 HEAD)
docker build -t <acr>.azurecr.io/ecom-api:$SHA .
az acr login -n <acr> && docker push <acr>.azurecr.io/ecom-api:$SHA
az webapp config container set -g rg-ecom-mini -n <app> --container-image-name <acr>.azurecr.io/ecom-api:$SHA
az webapp restart -g rg-ecom-mini -n <app>
python scripts/smoke_test.py https://<app>.azurewebsites.net
```

**Rollback:** run the same `container set` with the previous SHA, then restart. Old images stay in the registry.

From Week 11, GitHub Actions does these steps on every push to `main`.

### Verified in Week 8
| Check | Result |
| --- | --- |
| `scripts/smoke_test.py` against the public HTTPS URL | **10/10 passed**, on both F1 and B1, including the HTTP → HTTPS 301 redirect |
| Full shopping flow over HTTPS | Admin created a category, product and stock. A customer registered, added 3 items and checked out (₹3,897). Stock went 4 → 1, and the admin shipped the order. Verification data was deleted afterwards. |
| Database connection | TLS confirmed (`pg_stat_ssl.ssl = true`); Alembic at head `9b475d3a1915` |
| Container user | `appuser` (non-root), as in the Dockerfile |
| Redeploy `82ab820` (0.8.0) → `5d73b57` (0.8.1) | Live in 71 s |
| Rollback → `82ab820` | 0.8.0 live in 95 s |
| Roll forward → `5d73b57` | 0.8.1 live in 104 s (the final state) |
| First start of a newly pushed image | About 130 s: image pull, migration check, warm-up probe |
| Warm request time from India | About 0.3 s (`/health` and `/products`) |

| Image tag | Version | Can run with today's startup command? |
| --- | --- | --- |
| `08368f2`, `5fe4e16` | 0.4.0, 0.8.0 | **No.** Built before `app/scripts/start.py` existed. Not valid rollback targets. |
| `82ab820` | 0.8.0 | Yes |
| `5d73b57` | 0.8.1 | Yes (**live**) |

**Temporary B1:**
- To finish verification on the same day after the F1 quota was used up, the plan ran on **Basic B1 for 21 minutes**, approved by the owner, then went straight back to F1.
- Cost: about ₹0.61, at most ₹1.73 if billed as a full hour.
- Scaling between F1 and B1 did **not** change the outbound IPs, so the database firewall rules stayed valid.

## Day-to-day operations
| Task | Command |
| --- | --- |
| Check it works | `python scripts/smoke_test.py https://<app>.azurewebsites.net` |
| Follow the logs | `az webapp log tail -g rg-ecom-mini -n <app>` |
| Restart | `az webapp restart -g rg-ecom-mini -n <app>` |
| Create an admin | Temporary firewall rule for your IP, then run `create_admin` locally with the Azure `DATABASE_URL`. See "Creating an admin on Azure" below. `az webapp ssh` does **not** work, because the image deliberately has no SSH server. |
| Stop the app | `az webapp stop -g rg-ecom-mini -n <app>` (F1 is free anyway) |
| Stop the database | `az postgres flexible-server stop -g rg-ecom-mini -n <server>` (Azure restarts it after 7 days) |
| **Delete everything** | `az group delete -n rg-ecom-mini --yes` |

## Creating an admin on Azure
The API never lets anyone become an admin, and the Azure database starts empty, so the first admin is created with `app/scripts/create_admin.py`.

Since Week 9 the database connection uses `verify-full` TLS with a CA file path that exists inside the Docker image but not on Windows. So the command runs **inside the deployed Docker image**: the same environment as App Service, with full TLS verification. You need Docker Desktop running. In PowerShell:

```powershell
# 1. Allow your current public IP through the database firewall (temporary)
$myIp = Invoke-RestMethod https://api.ipify.org
az postgres flexible-server firewall-rule create -g rg-ecom-mini --server-name <server> --name temp-admin-pc --start-ip-address $myIp --end-ip-address $myIp --output none

# 2. Find the image the app runs, and get it onto this PC
$image = (az webapp show -g rg-ecom-mini -n <app> --query siteConfig.linuxFxVersion -o tsv) -replace '^DOCKER\|', ''
az acr login -n <registry>
docker pull $image

# 3. Put the Azure database URL into this terminal only (not shown, not saved)
$env:DATABASE_URL = az webapp config appsettings list -g rg-ecom-mini -n <app> --query "[?name=='DATABASE_URL'].value | [0]" -o tsv

# 4. Create the admin inside the image (type a new password twice; nothing is shown while typing)
docker run --rm -it -e DATABASE_URL -e SECRET_KEY=not-used-by-this-command-0123456789abcdef $image python -m app.scripts.create_admin you@example.com

# 5. Clean up
Remove-Item Env:DATABASE_URL
az postgres flexible-server firewall-rule delete -g rg-ecom-mini --server-name <server> --name temp-admin-pc --yes
```

- `-e DATABASE_URL` with no value passes the variable from your terminal into the container without writing it into the command.
- `SECRET_KEY` is required by the settings, but `create_admin` doesn't use it, so any 32+ character value works.
- `-it` makes the hidden password prompt work.

## F1 (free tier) limits to know
- **60 CPU-minutes a day.**
  - When the quota is used up, the app shows `QuotaExceeded` / "403 Site Disabled" until 00:00 UTC (05:30 IST). Nothing is billed.
  - **A crash-looping container uses the quota up fast.** That happened once in Week 8 (see the startup-command lesson above).
- **No Always On.** After about 20 idle minutes the container is unloaded, and the next request waits for a **cold start**: about 1–2 minutes when the image has to be pulled again.
- **1 GB of memory, 1 GB of storage, one instance, and no deployment slots.**
- These are fine for a demo. A production system would use at least B1.
