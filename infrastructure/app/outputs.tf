output "web_app_name" {
  value = azurerm_linux_web_app.api.name
}

output "web_app_url" {
  value = "https://${azurerm_linux_web_app.api.default_hostname}"
}

output "outbound_ip_count" {
  description = "How many firewall rules the database has for this app."
  value       = length(azurerm_linux_web_app.api.possible_outbound_ip_address_list)
}
