# Monitoring: where logs and telemetry are stored, and who gets alert emails.
# In the foundation layer so the history survives an app-layer rebuild. Not locked
# with prevent_destroy: it holds no business data.

# Log Analytics: one store for both the App Service platform logs and the
# Application Insights telemetry, queried with KQL.
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-ecom-mini"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.data_location # next to the web app
  sku                 = "PerGB2018"       # pay per GB, but the first 5 GB/month are free
  retention_in_days   = 30                # the minimum; included in the price
  # Hard ingestion cap: at most 0.1 GB/day, so at most ~3 GB/month, below the
  # free 5 GB. When the cap is reached, collection pauses until the next day.
  daily_quota_gb = 0.1
  tags           = var.tags
}

# Application Insights: request, error and log telemetry sent by the app itself
# (OpenTelemetry). Its data is stored in the workspace above.
resource "azurerm_application_insights" "main" {
  name                 = "appi-ecom-mini"
  resource_group_name  = azurerm_resource_group.main.name
  location             = var.data_location
  workspace_id         = azurerm_log_analytics_workspace.main.id
  application_type     = "web"
  daily_data_cap_in_gb = 0.1
  # No instrumentation-key authentication: the app must prove who it is with its
  # managed identity (role "Monitoring Metrics Publisher", app layer). The key in
  # the connection string alone cannot be used to send fake telemetry.
  local_authentication_enabled = false
  tags                         = var.tags
}

# Who is told when an alert fires. Emails are free.
resource "azurerm_monitor_action_group" "owner_email" {
  name                = "ag-ecom-mini-owner"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "ecomowner" # at most 12 characters, shown in the email
  tags                = var.tags

  email_receiver {
    name                    = "owner"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}
