# Azure Cost Log

A weekly record of Azure spending, so surprises are caught early. It takes about 5 minutes each week:
1. Portal → **Cost Management** → Cost analysis, or the *Student offer details* card: note the running total and the credit left.
2. `az resource list -o table`: list what exists, and stop or delete anything not needed.
3. Add a row below.

Hard cap: **₹5,000**. Budget alerts at ₹500 / ₹1,000 / ₹2,500 / ₹4,000 (see `docs/azure-cost-notes.md`).

| Date | Week | Project total so far (₹) | Credit left (₹) | Resources that exist | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | 7 | 0.00 | 9,599 | `rg-ecom-mini` (empty) | Budget `ecom-mini-budget` created (₹4,000/year, 5 alerts). Providers registered. The subscription had ₹0.14 of earlier spend from another project's lab, which isn't counted here. |
