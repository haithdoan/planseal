terraform {
  required_version = ">= 1.6"
}

variable "message" {
  description = "Synthetic value used by the credential-free example."
  type        = string
  default     = "planseal-example"
}

resource "terraform_data" "example" {
  input = var.message
}

output "result" {
  description = "Synthetic result produced by the built-in resource."
  value       = terraform_data.example.output
}
