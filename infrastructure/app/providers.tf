# Terraform signs in to Azure with the current `az login` session.
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id

  # The storage account has account keys switched off, so Terraform must use
  # Entra ID (the same `az login` identity) for storage operations too.
  storage_use_azuread = true
}
