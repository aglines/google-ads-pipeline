# Performance Optimization

## BigQuery Cost Analysis

Query to identify expensive operations:

```sql
SELECT
  user_email,
  query,
  total_bytes_processed / POW(10, 9) AS gb_processed,
  (total_bytes_billed / POW(10, 9)) * 5 AS estimated_cost_usd,
  creation_time
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
ORDER BY
  total_bytes_billed DESC
LIMIT 20;
```

## Optimizations Implemented

### 1. Table Clustering

Added clustering to `fct_keyword_performance` on `date` and `campaign_id` for efficient date range queries.

### 2. Materialization Strategy

- **Staging**: Views (low cost, always fresh)
- **Intermediate**: Ephemeral (no storage cost)
- **Fact tables**: Tables with partitioning (query performance)
- **Analytics**: Views (flexibility for ad-hoc queries)

### 3. Incremental Models

For production scale, convert `fct_keyword_performance` to incremental:

```sql
{{ config(
    materialized='incremental',
    unique_key='keyword_performance_id',
    partition_by={'field': 'date', 'data_type': 'date'},
    cluster_by=['campaign_id', 'keyword_id']
) }}
```

### 4. Query Optimization

- Use `SELECT` with specific columns instead of `SELECT *`
- Filter on partitioned columns first
- Avoid cross joins and large window functions

## Baseline Metrics

Current performance (synthetic data):
- Full dbt run: ~2-3 minutes
- DAG end-to-end: ~15-20 minutes
- BigQuery cost per run: <$0.01
- Total monthly cost (daily runs): <$1

## Monitoring Performance

Track these metrics over time:
- dbt model run duration
- BigQuery bytes processed per query
- Total pipeline execution time
- Table sizes and row counts
