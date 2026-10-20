# Infrastructure (Terraform)

The project's Azure setup, described as code. Concepts and design decisions are explained in [docs/terraform.md](../docs/terraform.md); this file is the **runbook**.

| Layer | Folder | What it contains | Can be destroyed? |
| --- | --- | --- | --- |
| Foundation | `foundation/` | Resource group, budget, container registry, PostgreSQL server and `ecom` database, storage account and `product-images` container, database passwords | **No.** `prevent_destroy` refuses. |
| App | `app/` | App Service plan, web app, its two role assignments, one database firewall rule per outbound IP, `SECRET_KEY` | **Yes**, at any time. Rebuild it with the steps below. |

The app layer reads the foundation's outputs from `foundation/terraform.tfstate`, so **always work on the foundation first**.

## One-time setup on a new PC
1. Install Terraform 1.15+ (`winget install Hashicorp.Terraform`) and the Azure CLI, then run `az login`.
2. In **both** folders, copy `terraform.tfvars.example` to `terraform.tfvars` and fill in the values. That file is git-ignored.
3. In both folders, run `terraform init`.

> **The state files (`terraform.tfstate`) live only on the PC that ran Terraform, and they contain the generated passwords.** They are git-ignored. Back them up somewhere private; never commit or share them. If they are lost, Terraform has to adopt the resources again with `import` blocks (git history shows the ones used in Week 10).

## Everyday commands
Run these from the repository root. (`-chdir` runs Terraform in that folder.)

```bash
terraform -chdir=infrastructure/foundation plan   # should say "No changes"
terraform -chdir=infrastructure/app plan          # should say "No changes"
terraform -chdir=infrastructure/app output        # web app name, URL, number of firewall rules
```

Always read the plan before `apply`. **Stop if it says "must be replaced" or "will be destroyed" for anything you didn't intend.**

> **Careful with plans of imported resources.** The first time Terraform adopted the existing web app, the plan printed the *old* values of `app_settings`, including the database password and `SECRET_KEY`, because Azure doesn't mark app settings as secret. Those values were rotated straight away. After adoption, Terraform's state marks them as sensitive, so plans no longer show them.

## Destroy and rebuild the app layer
Destroying the app layer stops the public API but keeps all data, images and the registry.

```bash
terraform -chdir=infrastructure/app destroy
```

Rebuilding takes **two** commands. The web app's outbound IP addresses only become known once it exists, and the firewall rules are generated from them:

```bash
terraform -chdir=infrastructure/app apply -target=azurerm_linux_web_app.api   # plan + web app
terraform -chdir=infrastructure/app apply                                      # roles + firewall rules
az webapp restart -g rg-ecom-mini -n <web-app-name>                             # start with roles and firewall in place
python scripts/smoke_test.py https://<web-app-name>.azurewebsites.net
```

- Creating the 31 firewall rules is slow, about 30 minutes, because PostgreSQL applies rule changes one at a time.
- A rebuilt app gets a **new `SECRET_KEY`**, so everyone has to log in again. The database (and its users) are unchanged.
- The rebuilt app runs the image in `image_tag` (`variables.tf`). Deploy a newer image afterwards as usual (see `docs/azure-deployment.md`).

## Temporarily use the paid B1 plan
Only with the owner's approval (about ₹1.73/hour). Go back to F1 straight afterwards:

```bash
terraform -chdir=infrastructure/app apply -var plan_sku=B1
terraform -chdir=infrastructure/app apply                   # back to the default F1
```

## Rotating the database password of `ecom_app`
1. Generate a new password: `terraform -chdir=infrastructure/foundation apply -replace=random_password.app_db_user`. This changes only the stored value; the server itself is untouched.
2. Open a temporary firewall rule for your IP (see `docs/azure-deployment.md`).
3. Set the password in the database (no values are printed):

   ```powershell
   $env:ADMIN_DATABASE_URL = terraform -chdir=infrastructure/foundation output -raw admin_database_url
   $env:APP_DB_PASSWORD    = terraform -chdir=infrastructure/foundation output -raw app_db_password
   python scripts/create_app_db_user.py
   Remove-Item Env:ADMIN_DATABASE_URL, Env:APP_DB_PASSWORD
   ```

4. Right away, `terraform -chdir=infrastructure/app apply`, which writes the new `DATABASE_URL` into the web app and restarts it.
5. Delete the temporary firewall rule.

Do step 3 **before** step 4. Then the running app's open connections keep working until it restarts with the new URL, and the container never boots with a password the database doesn't know yet.

## Guardrails
- **Never** remove `prevent_destroy` from the foundation without the owner's explicit OK. The registry, the database and the images are meant to survive.
- **Never** commit `terraform.tfstate*`, `terraform.tfvars`, `*.tfplan` or `.terraform/`. `.gitignore` covers all of them; `.terraform.lock.hcl` *is* committed.
- **Deployments change the running image outside Terraform.** The web app ignores changes to its image tag (`ignore_changes`), so `apply` never rolls back a newer deployment.
- **Emergency stop for everything**, including the locked parts: `az group delete -n rg-ecom-mini --yes`. Terraform's lock does not stop direct Azure commands.
