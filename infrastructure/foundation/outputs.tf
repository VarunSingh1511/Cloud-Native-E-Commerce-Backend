# Values the app layer (and the runbook) read from this layer's state.

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "data_location" {
  value = var.data_location
}

output "tags" {
  value = var.tags
}

output "registry_id" {
  value = azurerm_container_registry.main.id
}

output "registry_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "postgres_server_id" {
  value = azurerm_postgresql_flexible_server.main.id
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "storage_account_url" {
  value = trimsuffix(azurerm_storage_account.images.primary_blob_endpoint, "/")
}

output "images_container_name" {
  value = azurerm_storage_container.product_images.name
}

output "images_container_id" {
  description = "Azure resource ID of the images container (used as a role-assignment scope)."
  value       = azurerm_storage_container.product_images.id
}

output "github_deploy_client_id" {
  description = "Client ID of the GitHub Actions identity (GitHub secret AZURE_CLIENT_ID)."
  value       = azurerm_user_assigned_identity.github_deploy.client_id
}

output "github_deploy_principal_id" {
  description = "Object ID of the GitHub Actions identity, used by the app layer's role assignment."
  value       = azurerm_user_assigned_identity.github_deploy.principal_id
}

# --- secrets: marked sensitive, so Terraform never prints them ---------------

output "app_database_url" {
  description = "Connection string for the app: least-privilege user ecom_app, fully verified TLS."
  sensitive   = true
  value       = "postgresql+psycopg://ecom_app:${random_password.app_db_user.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/ecom?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt"
}

output "app_db_password" {
  description = "Password of ecom_app; scripts/create_app_db_user.py sets it in the database."
  sensitive   = true
  value       = random_password.app_db_user.result
}

output "admin_database_url" {
  description = "Server-admin connection string, for scripts/create_app_db_user.py only."
  sensitive   = true
  value       = "postgresql://ecomadmin:${random_password.postgres_admin.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/ecom?sslmode=require"
}
