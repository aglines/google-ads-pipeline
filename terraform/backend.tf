# Local backend for development
# For production, migrate to GCS backend:
#
# terraform {
#   backend "gcs" {
#     bucket = "your-project-id-terraform-state"
#     prefix = "google-ads-pipeline"
#   }
# }

terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
