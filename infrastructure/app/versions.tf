# Which Terraform and which provider plug-ins this layer needs. Exact versions,
# so every run uses the same code; .terraform.lock.hcl (committed) pins the builds.
terraform {
  required_version = ">= 1.15.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.8.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.9.1"
    }
  }
}
