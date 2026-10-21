# Monitoring for the web app. The workspace, Application Insights and the email
# action group are in the foundation layer; these parts belong to the web app and
# are destroyed and rebuilt with it.

# The app sends telemetry to Application Insights with its own identity.
resource "azurerm_role_assignment" "telemetry_publisher" {
  scope                = local.foundation.application_insights_id
  role_definition_name = "Monitoring Metrics Publisher" # send telemetry, nothing else
  principal_id         = azurerm_linux_web_app.api.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

# App Service's own logs, sent to Log Analytics. They cover what the app cannot
# report itself: e.g. a container that fails to start (console and platform logs).
resource "azurerm_monitor_diagnostic_setting" "web_app" {
  name                       = "to-log-analytics"
  target_resource_id         = azurerm_linux_web_app.api.id
  log_analytics_workspace_id = local.foundation.log_analytics_workspace_id

  enabled_log {
    category = "AppServiceHTTPLogs" # every HTTP request seen by the front end
  }
  enabled_log {
    category = "AppServiceConsoleLogs" # the container's stdout/stderr (uvicorn, tracebacks)
  }
  enabled_log {
    category = "AppServicePlatformLogs" # container start, stop and pull events
  }
}

# Email the owner when the API returns any server error (HTTP 5xx).
resource "azurerm_monitor_metric_alert" "http_5xx" {
  name                = "alert-ecom-mini-http-5xx"
  resource_group_name = local.foundation.resource_group_name
  scopes              = [azurerm_linux_web_app.api.id]
  description         = "The API returned at least one HTTP 5xx (server error) in the last 5 minutes."
  severity            = 2 # warning
  frequency           = "PT5M"
  window_size         = "PT5M"
  auto_mitigate       = true # resolves itself once a 5-minute window has no errors
  tags                = local.foundation.tags

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = local.foundation.alert_action_group_id
  }
}
