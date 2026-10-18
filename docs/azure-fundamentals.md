# Azure Fundamentals (Week 7 notes)

Short explanations of the cloud ideas this project uses, written for interview preparation.

## IaaS, PaaS, SaaS
| Model | You manage | The provider manages | Example in this project |
| --- | --- | --- | --- |
| **IaaS** (Infrastructure as a Service) | The OS, runtime, patches and app | Hardware, network, virtualisation | *Not used.* A virtual machine running our Docker container would be IaaS. |
| **PaaS** (Platform as a Service) | Only the app and its settings | Also the OS, runtime, scaling and patching | **App Service** (runs our FastAPI code) and **Azure Database for PostgreSQL** (a managed database) |
| **SaaS** (Software as a Service) | Just use it | Everything | Microsoft Entra ID (sign-in), Outlook (the budget alert emails) |

**Why PaaS here:**
- No servers to patch, and backups and HTTPS come built in.
- Free tiers exist for this project's scale.
- More time goes into the DevOps work (Terraform, CI/CD) and less into administering machines.
- The trade-off is less control (fixed runtimes, F1 CPU limits).

## Regions
- A **region** is a set of datacentres in one geographic area, such as India South Central in Hyderabad.
- Choose the one closest to users for low latency, and one where all the needed services exist.
- Keep everything in **one** region. Traffic between regions is slower and can cost money.
- **Our case:** the student subscription has an *Azure Policy* that allows only 5 regions. Central India is not one of them, so we use **India South Central**.

## Subscriptions, resource groups and tags
- A **subscription** is the billing and access boundary. Ours is "Azure for Students", where the credit is spent.
- A **resource group** is a folder that holds a project's resources. Deleting the group deletes everything in it, which makes it our **emergency stop**. Ours is `rg-ecom-mini`.
- **Tags** are labels such as `project=ecom-mini`. In Cost Management, filtering by tag shows the cost of one project.

## Resource providers
Each Azure service is offered by a *resource provider*, such as `Microsoft.Web` for App Service or `Microsoft.DBforPostgreSQL` for the database. A subscription has to **register** a provider before it can create that kind of resource. Registering is free and creates nothing.

## Managed services
A **managed service** is one where Azure runs the hard parts for us. With Azure Database for PostgreSQL, Azure handles:
- installation and patching
- backups and point-in-time restore
- high availability options
- monitoring

We still own the schema, which Alembic manages, and the data.

## Secrets and configuration
The rule from Week 1 continues: **settings come from environment variables, and secrets never go in the code or the repo.**
- **App Service "app settings"** become environment variables inside the app. `DATABASE_URL` and `SECRET_KEY` will be set there in Week 8. Our `Settings` class reads them with no code change.
- **Azure Key Vault** is a dedicated secrets store, with access control and audit logs. It's worth knowing for interviews. This project keeps to app settings for simplicity.
- **Deploying from GitHub Actions (Week 11):** we will prefer **OIDC federated credentials**, which let GitHub prove its identity to Azure with no stored password.

## Cost management
- **Free amounts:** Azure for Students lists them under *Free services*, such as 750 hours of PostgreSQL B1ms. Staying inside them costs ₹0.
- **Budgets** compare spending against an amount and **send alerts**. **They never stop resources.**
- **What actually stops spending:**
  - deleting resources (or the resource group)
  - the credit running out (on a student subscription the services are switched off rather than billed)
  - Terraform `destroy` from Week 10
- **Forecast alerts** warn when spending is *heading* past the budget, before it actually does.
- **Weekly habit:** record the total in `docs/azure-cost-log.md`.

## What exists in Azure after Week 7
| Thing | Cost |
| --- | --- |
| Budget `ecom-mini-budget` (₹4,000/year, 5 alerts) | ₹0 |
| 5 registered resource providers | ₹0 |
| Resource group `rg-ecom-mini` in India South Central, tagged and **empty** | ₹0 |
