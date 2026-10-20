# ONE-TIME adoption of the app resources created by hand in Weeks 8-9.
# This file is deleted right after the first successful apply: once the app layer
# can be destroyed and rebuilt, these old IDs no longer exist, and import blocks
# for missing objects make Terraform fail. (Git history keeps it.)

locals {
  rg_id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-ecom-mini"
}

import {
  to = azurerm_service_plan.main
  id = "${local.rg_id}/providers/Microsoft.Web/serverFarms/asp-ecom-mini"
}

import {
  to = azurerm_linux_web_app.api
  id = "${local.rg_id}/providers/Microsoft.Web/sites/app-ecom-mini-${var.name_suffix}"
}

import {
  to = azurerm_role_assignment.registry_pull
  id = "${local.rg_id}/providers/Microsoft.ContainerRegistry/registries/acrecommini${var.name_suffix}/providers/Microsoft.Authorization/roleAssignments/e4e9babc-4a38-4753-a861-990f6a73bf44"
}

import {
  to = azurerm_role_assignment.images_writer
  id = "${local.rg_id}/providers/Microsoft.Storage/storageAccounts/stecommini${var.name_suffix}/blobServices/default/containers/product-images/providers/Microsoft.Authorization/roleAssignments/9c760f4b-81e8-44f5-8ea9-f686d8bcc125"
}
