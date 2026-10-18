# Azure Cost Notes

Findings from Week 7 (checked on 2026-10-18) and the cheapest path for every Azure service in this project. Re-check prices before creating anything. Free offers and prices change.

**Rule:** hard cap ₹5,000 for the whole project, with a target of ₹0–1,500. Nothing is created without the owner's approval, and resources are deleted when not needed.

## The subscription
| Item | Value |
| --- | --- |
| Offer | **Azure for Students**, a university account with MFA required |
| Credit | **₹9,599**, with ₹9,599 left on 2026-10-18 |
| Credit expiry | **8 September 2027** |
| Billing currency | **INR**, so budget amounts are entered in rupees |
| Role | Owner of the subscription |
| When the credit runs out or expires | Services are switched off, **not** billed to a card, unless the subscription is upgraded to pay-as-you-go. **Never upgrade.** |
| Allowed regions (subscription policy) | `indiasouthcentral`, `malaysiawest`, `koreacentral`, `eastasia`, `indonesiacentral`. **Central India is not allowed.** |

The credit (₹9,599) is **larger than our ₹5,000 cap**, so the credit alone would not stop us from going over the cap. The budget alerts below are what protect it.

## Region: India South Central (`indiasouthcentral`)
- **Every service we need is available there:** App Service F1 Linux, PostgreSQL Flexible B1ms, Storage, Log Analytics and Application Insights. That was checked with the Azure CLI.
- **It is the only allowed region in India.** That gives the lowest latency for demos from India and keeps data in India.
- **Price is not a reason to pick a different region.** The paid prices of the other four allowed regions are within about ±10%, and the free amounts apply in any region.

## Service-by-service: free or not?
Prices are from the Azure Retail Prices API in INR, for India South Central, on 2026-10-18. "Free" means it is covered by the Azure for Students free amounts shown in the portal under *Free services*.

| Service | What we need | Free amount (portal) | Paid price if we go beyond it | Plan |
| --- | --- | --- | --- | --- |
| **App Service** | 1 small web API | Always free: **F1, up to 10 apps, 1 GB storage, 60 CPU-minutes a day** | B1 Linux ₹1.73/hour, about ₹1,260/month | **F1 with code deploy: ₹0** |
| **PostgreSQL Flexible Server** | 1 tiny database | **750 hours a month of Burstable B1ms, 32 GB storage, 32 GB backup**, for 12 months | B1ms ₹2.35/hour, about ₹56/day; storage about ₹12.6/GiB-month | **B1ms, 32 GB, 7-day backups: ₹0.** 750 h covers a full month (at most 744 h) for **one** server. |
| **Blob Storage** | A few product images | **5 GB** LRS hot, 20,000 reads and 10,000 writes a month | about ₹1.8/GB-month | **1 storage account, 1 container: ₹0** |
| **Container Registry** | Optional (container deploy) | **1 Standard registry**, 100 GB | - | Decided in Week 8. Only useful if the App Service plan can run containers. |
| **Log Analytics / Application Insights** | Logs and metrics | First **5 GB a month** of ingestion is free | ₹309/GB after that | **Set a daily cap** (for example 0.1 GB) so we can never pay |
| **Resource group, budgets, provider registration** | Organisation | Always free | - | ₹0 |

### Conditions that would make "free" cost money
- **PostgreSQL:**
  - A second server: the 750 hours are shared, so two servers running all month use about 1,488 hours.
  - Any SKU other than B1ms.
  - Storage above 32 GB, or geo-redundant backup.
  - Running after the 12-month free period ends.
- **App Service:** upgrading the plan from F1 to B1. F1's daily CPU quota pauses the app when it is used up; it does not bill.
- **Logs:** ingesting more than 5 GB a month. The daily cap prevents it.
- **Any resource in another region:** the policy blocks this anyway.

## Cheapest path (the default for Weeks 8–12)
1. **App Service F1** (Linux, Python), with **code deploy**: GitHub Actions pushes the code. **₹0.**
2. **PostgreSQL Flexible Server B1ms**, 32 GB, 7-day backups, one server only. **₹0** within the 750 hours.
3. **One Storage account** (Standard LRS) with one Blob container for product images. **₹0** within 5 GB.
4. **Application Insights**, workspace-based, with a daily cap. **₹0** within 5 GB.
5. From Week 10, Terraform creates and destroys everything, so the environment exists only when needed.

**Expected total: ₹0.** The budget catches mistakes.

## Fallback plan if something turns out not to be free
| If... | Then... | Worst-case cost |
| --- | --- | --- |
| PostgreSQL bills despite the free offer | Run it only during work sessions and **delete it afterwards**. Terraform recreates it in minutes. Stopping is not enough: storage is still billed, and Azure restarts stopped servers after 7 days. | about ₹70/day while it exists (compute plus storage) |
| F1 is too limited for a demo (CPU quota, cold starts) | Switch to B1 for the demo days only, then back to F1 | about ₹42/day |
| A container deploy is wanted (optional stretch) | B1 plan plus the free Standard registry, for a few days only | about ₹42/day |

## Budget alerts (created in Week 7)
| Budget | Scope | Period | Amount | Alerts (sent to the owner's university email) |
| --- | --- | --- | --- | --- |
| `ecom-mini-budget` | Whole subscription | Annual, 2026-10-01 to 2027-09-30 | **₹4,000** | Actual ₹500 (12.5%), ₹1,000 (25%), ₹2,500 (62.5%), ₹4,000 (100%), plus a **forecast** of 100% |

- **Why a subscription-wide budget:** it also catches anything created outside `rg-ecom-mini` by mistake, such as the `NetworkWatcherRG` group Azure creates automatically.
- **Why ₹4,000 and not ₹5,000:** the last alert arrives with ₹1,000 still in hand.
- **Budgets only send emails. They do not stop anything.** The real controls are deleting resources (or the whole resource group) and the weekly cost check.
- An older budget, `lab-credit-budget` (₹100), belongs to another project and is left unchanged.

## Emergency stop
```bash
az group delete -n rg-ecom-mini --yes     # deletes everything this project created
az resource list -o table                 # confirm nothing is left anywhere
```
