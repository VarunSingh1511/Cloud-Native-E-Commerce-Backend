# One-time adoption of resources that were first created by hand with `az`
# (Weeks 7-9). An import block tells Terraform "this existing resource is the one
# in my code" without touching it. Once they are in the state, these blocks are
# no-ops; they are kept as documentation of where each resource came from.

locals {
  rg_id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-ecom-mini"
}

import {
  to = azurerm_resource_group.main
  id = local.rg_id
}

import {
  to = azurerm_consumption_budget_subscription.project
  id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Consumption/budgets/ecom-mini-budget"
}

import {
  to = azurerm_container_registry.main
  id = "${local.rg_id}/providers/Microsoft.ContainerRegistry/registries/acrecommini${var.name_suffix}"
}

import {
  to = azurerm_postgresql_flexible_server.main
  id = "${local.rg_id}/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-ecom-mini-my-${var.name_suffix}"
}

import {
  to = azurerm_postgresql_flexible_server_database.ecom
  id = "${local.rg_id}/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-ecom-mini-my-${var.name_suffix}/databases/ecom"
}

import {
  to = azurerm_storage_account.images
  id = "${local.rg_id}/providers/Microsoft.Storage/storageAccounts/stecommini${var.name_suffix}"
}

import {
  to = azurerm_storage_container.product_images
  id = "${local.rg_id}/providers/Microsoft.Storage/storageAccounts/stecommini${var.name_suffix}/blobServices/default/containers/product-images"
}
