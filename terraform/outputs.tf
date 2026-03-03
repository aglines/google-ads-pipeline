# Outputs for reference after terraform apply

output "bigquery_datasets" {
  description = "BigQuery dataset IDs"
  value = {
    raw_google_ads     = google_bigquery_dataset.raw_google_ads.dataset_id
    staging_google_ads = google_bigquery_dataset.staging_google_ads.dataset_id
    staging_trends     = google_bigquery_dataset.staging_trends.dataset_id
    intermediate       = google_bigquery_dataset.intermediate.dataset_id
    marts_marketing    = google_bigquery_dataset.marts_marketing.dataset_id
    marts_analytics    = google_bigquery_dataset.marts_analytics.dataset_id
  }
}

output "storage_buckets" {
  description = "GCS bucket names"
  value = {
    raw_data       = google_storage_bucket.raw_data.name
    processed_data = google_storage_bucket.processed_data.name
  }
}
