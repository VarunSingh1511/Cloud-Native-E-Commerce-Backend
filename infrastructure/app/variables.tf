# Values that differ per person/subscription live in terraform.tfvars (git-ignored).

variable "subscription_id" {
  description = "Azure subscription ID. Not a password, but kept out of the repository."
  type        = string
}

variable "name_suffix" {
  description = "Random 4-character suffix that makes the web app name globally unique."
  type        = string
}

variable "image_tag" {
  description = <<-EOT
    Image tag (git commit SHA) used when the web app is CREATED. Later deployments
    change the running image outside Terraform (see ignore_changes in main.tf).
  EOT
  type        = string
  default     = "a88926b"
}
