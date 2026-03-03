# Monitoring Guide

## Local Airflow Monitoring

### Airflow Web UI (localhost:8080)

**DAG Monitoring:**
- View all DAGs and their current status
- Check last run success/failure
- Monitor task duration trends
- Review task logs in real-time

**Key Metrics to Monitor:**
- DAG run duration (should be <30 minutes for synthetic data)
- Task failure rate (should be 0%)
- Data quality test pass rate (should be 100%)
- Row counts in staging tables (should match expected volumes)

### Email Alerts for DAG Failures

Configure in `airflow.cfg` or environment variables:

```ini
[email]
email_backend = airflow.utils.email.send_email_smtp
email_conn_id = smtp_default

[smtp]
smtp_host = smtp.gmail.com
smtp_starttls = True
smtp_ssl = False
smtp_user = your-email@gmail.com
smtp_password = your-app-password
smtp_port = 587
smtp_mail_from = your-email@gmail.com
```

Add to DAG default_args:

```python
default_args = {
    'email': ['alerts@yourcompany.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}
```

### Logging Best Practices

**Structured Logging in Python Tasks:**

```python
import logging
import json

logger = logging.getLogger(__name__)

# Log key metrics as JSON
logger.info(json.dumps({
    'event': 'extraction_complete',
    'rows_extracted': row_count,
    'duration_seconds': duration,
    'timestamp': datetime.now().isoformat()
}))
```

**Log Levels:**
- `ERROR`: Task failures, data quality violations
- `WARNING`: Anomalies, performance degradation
- `INFO`: Task completion, row counts, key metrics
- `DEBUG`: Detailed execution steps

### Monitoring Checklist

Daily:
- [ ] Check DAG runs completed successfully
- [ ] Review error logs if any failures
- [ ] Verify row counts in BigQuery tables
- [ ] Check dbt test results

Weekly:
- [ ] Review task duration trends
- [ ] Check BigQuery query costs
- [ ] Review data freshness
- [ ] Validate bid recommendation quality

### BigQuery Monitoring

**Table Row Counts:**

```sql
SELECT
  table_name,
  row_count,
  TIMESTAMP_MILLIS(creation_time) AS created,
  TIMESTAMP_MILLIS(CAST(last_modified_time AS INT64)) AS last_modified
FROM
  `PROJECT_ID.marts_marketing.__TABLES__`
ORDER BY
  last_modified DESC;
```

**Query Cost Analysis:**

```sql
SELECT
  user_email,
  query,
  total_bytes_processed / POW(10, 9) AS gb_processed,
  total_bytes_billed / POW(10, 9) AS gb_billed,
  (total_bytes_billed / POW(10, 9)) * 5 AS estimated_cost_usd,
  creation_time
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
ORDER BY
  total_bytes_billed DESC
LIMIT 20;
```

## Optional: Cloud Monitoring (for future Composer deployment)

**Note:** This section is for documentation only. Cloud Monitoring is not required for local Airflow deployment.

If deploying to Cloud Composer in the future:
- Enable Cloud Logging for Airflow logs
- Create log-based metrics for error patterns
- Set up Cloud Monitoring dashboards
- Configure budget alerts for BigQuery costs
- Set up uptime checks for Airflow webserver

See `docs/production_deployment_guide.md` for Cloud Composer deployment details.
