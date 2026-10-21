# APP layer: the parts that hold no data and can be destroyed and rebuilt at any
# time (`terraform destroy` here never touches the database, images or registry,
# which live in the foundation layer).

# Read the foundation layer's outputs (registry, database, storage, secrets)
# straight from its local state file.
data "terraform_remote_state" "foundation" {
  backend = "local"
  config = {
    path = "${path.module}/../foundation/terraform.tfstate"
  }
}

locals {
  foundation = data.terraform_remote_state.foundation.outputs
}

# The app's JWT signing key. Generated once and kept in the (local) state file.
resource "random_password" "secret_key" {
  length  = 48
  special = false
}

resource "azurerm_service_plan" "main" {
  name                = "asp-ecom-mini"
  resource_group_name = local.foundation.resource_group_name
  location            = local.foundation.data_location # next to the database
  os_type             = "Linux"
  sku_name            = var.plan_sku # F1 (free) by default; see variables.tf
  tags                = local.foundation.tags
}

resource "azurerm_linux_web_app" "api" {
  name                    = "app-ecom-mini-${var.name_suffix}"
  resource_group_name     = local.foundation.resource_group_name
  location                = local.foundation.data_location
  service_plan_id         = azurerm_service_plan.main.id
  https_only              = true
  client_affinity_enabled = true
  tags                    = local.foundation.tags

  # No password-based publishing (FTP / WebDeploy). Deployments go through the
  # registry. The provider's defaults would switch these back on.
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  # Azure creates and manages this identity's credentials; the app uses it to
  # pull images and to write product images, so no passwords or keys are needed.
  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = false # not available on F1
    use_32_bit_worker                       = true  # F1 runs 32-bit workers
    ftps_state                              = "Disabled"
    minimum_tls_version                     = "1.2"
    scm_minimum_tls_version                 = "1.2"
    http2_enabled                           = true
    health_check_path                       = "/health"
    health_check_eviction_time_in_min       = 10
    app_command_line                        = "python -m app.scripts.start" # migrate, then serve
    container_registry_use_managed_identity = true

    application_stack {
      docker_registry_url = "https://${local.foundation.registry_login_server}"
      docker_image_name   = "ecom-api:${var.image_tag}"
    }
  }

  # App settings become environment variables inside the container, which
  # app/core/config.py reads. Values read from the foundation's state lose their
  # "sensitive" mark, so sensitive() hides them from plan output again.
  app_settings = {
    DATABASE_URL                        = sensitive(local.foundation.app_database_url)
    SECRET_KEY                          = random_password.secret_key.result
    ENVIRONMENT                         = "production"
    ACCESS_TOKEN_EXPIRE_MINUTES         = "30"
    WEBSITES_PORT                       = "8000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    AZURE_STORAGE_ACCOUNT_URL           = local.foundation.storage_account_url
    AZURE_STORAGE_CONTAINER             = local.foundation.images_container_name
    # Application Insights (app/core/telemetry.py). The app authenticates with its
    # managed identity; key authentication is disabled (see monitoring.tf).
    APPLICATIONINSIGHTS_CONNECTION_STRING = sensitive(local.foundation.application_insights_connection_string)
    # Do not record App Service's health probe (once a minute) as telemetry.
    OTEL_PYTHON_FASTAPI_EXCLUDED_URLS = "/health$"
  }

  logs {
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb   = 100
      }
    }
  }

  lifecycle {
    # Deployments change the running image (by hand now, GitHub Actions from Week 11).
    # Terraform only sets the image when it CREATES the app, and must not "undo"
    # a newer deployment on the next apply.
    ignore_changes = [site_config[0].application_stack[0].docker_image_name]
  }
}

# ------------------------------------------------------ least-privilege roles
resource "azurerm_role_assignment" "registry_pull" {
  scope                = local.foundation.registry_id
  role_definition_name = "AcrPull" # download images, nothing else
  principal_id         = azurerm_linux_web_app.api.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "images_writer" {
  scope                = local.foundation.images_container_id # this one container only
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_web_app.api.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

# GitHub Actions (foundation identity) may change this web app's image and restart
# it. Scoped to this one web app: no access to the plan, database or storage.
resource "azurerm_role_assignment" "github_deploy" {
  scope                = azurerm_linux_web_app.api.id
  role_definition_name = "Website Contributor"
  principal_id         = local.foundation.github_deploy_principal_id
  principal_type       = "ServicePrincipal"
}

# ----------------------------------------------------------- database firewall
# One rule per address the web app may use for outgoing connections. Generated
# from the app itself, so the list can never drift out of date.
# Note: for a brand-new web app these addresses are unknown until it exists, so a
# rebuild applies the web app first (see infrastructure/README.md).
resource "azurerm_postgresql_flexible_server_firewall_rule" "app_outbound" {
  for_each = toset(azurerm_linux_web_app.api.possible_outbound_ip_address_list)

  name             = "app-${replace(each.value, ".", "-")}"
  server_id        = local.foundation.postgres_server_id
  start_ip_address = each.value
  end_ip_address   = each.value
}
