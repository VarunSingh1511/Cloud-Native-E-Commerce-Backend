# CI/CD with GitHub Actions (Week 11)

Every change is now tested automatically, and every change merged into `main` is deployed to Azure automatically, with no password stored anywhere.

```text
pull request ──► Tests ─┬─► Docker image builds and starts            (stops here: PRs never deploy)
                Terraform ┘

push to main ──► Tests ─┬─► Docker image ─┬─► Deploy to Azure
                Terraform ┘─────────────────┘   OIDC login → build + push ecom-api:<sha>
                                                → point the web app at it → restart
                                                → wait for /health → smoke test (10 checks)
```

Files:
- [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml): the pipeline above.
- [`.github/workflows/rollback.yml`](../.github/workflows/rollback.yml): deploys an image that is already in the registry, by hand.
- [`scripts/deploy.sh`](../scripts/deploy.sh): the deploy steps shared by both workflows.

## Concepts

| Term | Meaning here |
| --- | --- |
| **CI** (continuous integration) | Every proposed change is checked automatically before it is merged: tests, migrations, Terraform, Docker build. |
| **CD** (continuous deployment) | Every change merged into `main` goes live automatically if all checks pass. There is no manual step. |
| **Workflow** | A YAML file in `.github/workflows/`. GitHub runs it when its trigger (`on:`) happens. |
| **Job** | A group of steps that runs on one fresh virtual machine (a **runner**, here `ubuntu-24.04`). Jobs run in parallel unless `needs:` orders them. |
| **Step** | One command (`run:`) or one reusable **action** (`uses:`), such as checking out the code or logging in to Azure. |
| **Service container** | A container GitHub starts next to a job. The `test` job gets a throwaway PostgreSQL 16.15, like the `db` service in Docker Compose. |
| **Secret** | A value GitHub stores encrypted and hides as `***` in the logs. |
| **Environment** | A named deployment target (`production`) with its own rules and secrets. Here it allows only the `main` branch. |

## The jobs

| Job | Runs on | What it proves |
| --- | --- | --- |
| **Tests** | PRs and `main` | All 187 tests pass against a real PostgreSQL. `alembic check` confirms the models and the migrations describe the same schema. |
| **Terraform** | PRs and `main` | The Terraform code is formatted (`fmt -check`) and valid (`validate`). This needs no Azure login and no state; it checks the code, not the live setup. |
| **Docker image** | PRs and `main`, after Tests | The image builds and starts: Docker's own HEALTHCHECK reports `healthy`. `/health` needs no database, so dummy settings are enough. |
| **Deploy** | **Only a push to `main`**, after all three | Builds and pushes `ecom-api:<first 7 characters of the commit SHA>`, points the web app at it, restarts it, waits until `/health` answers, then runs `scripts/smoke_test.py`. |

A failure stops everything that depends on it. This was demonstrated with a deliberately failing test (`assert 1 + 1 == 3`): Tests went red, and the image and deploy jobs were skipped. The commit was then reverted.

## How GitHub logs in to Azure without a password (OIDC)

Old way: create a service principal with a client secret and paste that secret into GitHub. It is a long-lived password that can leak, and it must be rotated.

Used here, **OpenID Connect (OIDC) workload identity federation**:
1. The deploy job has `permissions: id-token: write`. That lets it ask GitHub for a short-lived token signed by GitHub, stating who it is: `repo:VarunSingh1511@184231506/Cloud-Native-E-Commerce-Backend@1341839399:environment:production`.
2. `azure/login` sends that token to Microsoft Entra ID.
3. Entra ID checks it against the **federated credential** of our deploy identity. It must have the same issuer (`token.actions.githubusercontent.com`), the same audience (`api://AzureADTokenExchange`) and **exactly the same subject**. If they match, Entra ID returns an Azure access token valid for about an hour.

Nothing secret is stored in GitHub. The five "secrets" (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ACR_NAME`, `WEBAPP_NAME`) are identifiers, not passwords. They are secrets only so they appear as `***` in the logs, because the repository is public. They are stored as **environment** secrets, so only jobs in `production` can read them.

**The deploy identity** (`id-ecom-mini-github-deploy`) is a user-assigned managed identity, created by Terraform:
- It is used instead of an Entra "app registration" because university tenants often block app registrations. A managed identity is just a resource in our own subscription.
- **Least privilege:**

  | Role | Scope | Allows |
  | --- | --- | --- |
  | AcrPush | the container registry only | push and pull images |
  | Website Contributor | the web app only | change its image, restart it |

  It cannot touch the database, storage, the plan or anything else.
- The identity, its federated credential and the AcrPush role are in the Terraform **foundation** layer, so the client ID never changes. The Website Contributor role is in the **app** layer, created and destroyed together with the web app.

## Security choices

| Risk | What the workflow does |
| --- | --- |
| A pull request from a fork tries to steal secrets or deploy | The trigger is `pull_request`, never `pull_request_target`, so fork PRs get no secrets and no OIDC token. The deploy job also requires a push to `main` and the `production` environment, which only accepts `main`. |
| A third-party action is changed after we start using it | Every action is pinned to a full commit SHA, with its version in a comment. A tag can be moved to other code; a commit SHA cannot. |
| A job does more than it should | `permissions: contents: read` by default. Only the deploy jobs get `id-token: write`. |
| Shell injection through the rollback input | The tag goes through an `env:` variable, never `${{ }}` inside the script, and must match `^[0-9a-f]{7}$`. |
| Resource names in public logs | They are secrets, so the logs show `***.azurecr.io/ecom-api:34e7d57` and `https://***.azurewebsites.net` (checked). |
| Repository renamed or deleted, then re-created by someone else ("repo-jacking") | GitHub's token names the repository by its numeric owner and repository IDs, and the federated credential trusts exactly those IDs. |
| Two deployments at once | `concurrency: deploy-production` with `cancel-in-progress: false`: a newer deploy waits, and a running one is never interrupted halfway. |

## Manual run (added in Week 12)

**Actions → CI/CD → Run workflow** (`workflow_dispatch`) runs the whole pipeline on demand: tests, Terraform checks, image and, **only when run on `main`**, the deploy. Run on any other branch, the deploy job is skipped by its `if:` condition, and the `production` environment refuses non-`main` branches as well.

It exists because GitHub sometimes fails to start the push-triggered run (see "Problems met and fixed"). It's also a convenient way to redeploy `main` right before a demo.

## Rollback

**Actions → Rollback → Run workflow**, then enter an image tag (a 7-character commit SHA that exists in the registry). It checks the tag format, confirms the image exists (`docker manifest inspect`), then runs the same `scripts/deploy.sh` with the smoke test. The same button rolls forward again with the newer tag. No build happens, so it is quicker than a deploy.

Rollback is manual on purpose. An automatic rollback is triggered by a container that fails to start, and on F1 a crash-looping container burns the daily CPU quota (Week 8). A rollback that can't be tested safely isn't worth having. The `Image tag` table in [azure-deployment.md](azure-deployment.md) lists which old tags are valid rollback targets.

## Results (2026-10-21)

| Run | Result | Time |
| --- | --- | --- |
| PR with a deliberately failing test | Tests ✗; image and deploy skipped | 41 s |
| PR after the revert | Tests, Terraform and image ✓; deploy skipped | about 1 min |
| Push to `main` (merge of PR #1, `34e7d57`) | All 4 jobs ✓; live image `ecom-api:34e7d57`; smoke test 10/10 | 2 min 41 s in total; the deploy job took 2 min 35 s |
| Rollback → `a88926b` | ✓, smoke test 10/10 | 128 s |
| Roll forward → `34e7d57` | ✓, smoke test 10/10 | 127 s |

After the CI deploys, `terraform plan` shows **No changes** for both layers. The web app's image is in `ignore_changes`, and Azure stores it as `<registry>/ecom-api:<tag>`, which Terraform reads back correctly, so the Week 10 doubled-registry problem cannot come back.

## Problems met and fixed

| Problem | Cause | Fix |
| --- | --- | --- |
| First deploy: `AADSTS700213: No matching federated identity record found for presented assertion subject` | GitHub's OIDC token names the repository as `owner@ownerID/repo@repoID`. The federated credential had the name-only form `repo:owner/repo:environment:production`. | The subject in Terraform now uses the ID form (`var.github_repository`). One in-place change; then "Re-run failed jobs". This form is also safer (see repo-jacking above). |
| Week 12: merges of PRs #4 and #5 started no CI/CD run | A GitHub incident ("Delays for Pull Requests and Webhook deliveries", opened 14:52 UTC). For PR #4's merge commit, GitHub's API even answered 422 (commit not found) while `main` pointed at it. The workflow was active and unchanged, and the commit message had no skip marker. | Added the manual **Run workflow** trigger (`workflow_dispatch`) and started the pipeline by hand on `main`. It deployed both fixes. |

## Day-to-day

- **Deploy:** open a PR, wait for the green checks, and merge. That's all. Then `git pull` locally.
- **Check what's live:** `az webapp config show -g rg-ecom-mini -n <app> --query linuxFxVersion -o tsv`.
- **Manual deploy (fallback):** `WEBAPP_NAME=<app> RESOURCE_GROUP=rg-ecom-mini bash scripts/deploy.sh <acr>.azurecr.io/ecom-api:<sha>`, after `az login`. See [azure-deployment.md](azure-deployment.md).
- **F1 quota:** each deploy uses a few of F1's 60 CPU-minutes per day. Avoid more than about 10 deploys a day. If the quota runs out, the app is stopped until it resets at 05:30 IST.
- **Cost:** ₹0. Actions minutes are free for public repositories, and the identity, federated credential and roles cost nothing. Each image adds only its small code layer to the registry.

Not done, by choice: Terraform in CI (the state is local and holds secrets), staging slots (F1 has none), branch protection rules, Dependabot, and automatic rollback (see above).
