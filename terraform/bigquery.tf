# BigQuery datasets for the Google Ads pipeline
# Matches the dataset names in .env.example

resource "google_bigquery_dataset" "raw_google_ads" {
  dataset_id  = "raw_google_ads"
  description = "Raw data from Google Ads extraction"
  location    = var.data_location
  project     = var.project_id

  labels = {
    environment = var.environment
    layer       = "raw"
  }
}

resource "google_bigquery_dataset" "staging_google_ads" {
  dataset_id  = "staging_google_ads"
  description = "Staged and cleaned Google Ads data"
  location    = var.data_location
  project     = var.project_id

  labels = {
    environment = var.environment
    layer       = "staging"
  }
}

resource "google_bigquery_dataset" "staging_trends" {
  dataset_id  = "staging_trends"
  description = "Staged Google Trends and external data"
  location    = var.data_location
  project     = var.project_id

  labels = {
    environment = var.environment
    layer       = "staging"
  }
}

resource "google_bigquery_dataset" "intermediate" {
  dataset_id  = "intermediate"
  description = "Intermediate transformations and joins"
  location    = var.data_location
  project     = var.project_id

  labels = {
    environment = var.environment
    layer       = "intermediate"
  }
}

resource "google_bigquery_dataset" "marts_marketing" {
  dataset_id  = "marts_marketing"
  description = "Marketing data mart - dimensions and facts"
  location    = var.data_location
  project     = var.project_id

  labels = {
    environment = var.environment
    layer       = "marts"
  }
}

resource "google_bigquery_dataset" "marts_analytics" {
  dataset_id  = "marts_analytics"
  description = "Analytics data mart - aggregated views"
  location    = var.data_location
  project     = var.project_id

  labels = {
    environment = var.environment
    layer       = "marts"
  }
}
