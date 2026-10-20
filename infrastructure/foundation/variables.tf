# Values that differ per person/subscription live in terraform.tfvars (git-ignored).
# terraform.tfvars.example shows the format.

variable "subscription_id" {
  description = "Azure subscription ID. Not a password, but kept out of the repository."
  type        = string
}

variable "name_suffix" {
  description = "Random 4-character suffix that makes global names unique (registry, server, storage)."
  type        = string
}

variable "alert_email" {
  description = "Email address that receives the budget alerts."
  type        = string
}

variable "registry_location" {
  description = "Region of the resource group and the container registry (Week 7 choice)."
  type        = string
  default     = "indiasouthcentral"
}

variable "data_location" {
  description = "Region of PostgreSQL and storage: next to the web app (Week 8: no B1ms capacity in India)."
  type        = string
  default     = "malaysiawest"
}

variable "tags" {
  description = "Tags on every resource, so Cost Management can filter by project."
  type        = map(string)
  default = {
    project     = "ecom-mini"
    environment = "dev"
    owner       = "varun"
    managed-by  = "terraform"
  }
}
