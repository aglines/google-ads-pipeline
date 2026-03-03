# Google Ads Bid Optimization Dashboard

Streamlit-based interactive dashboard for visualizing Google Ads performance and bid recommendations.

## Features

- **KPI Overview**: Real-time metrics (impressions, clicks, cost, conversions, ROAS)
- **Performance Trends**: Time-series charts for ROAS, cost vs revenue, clicks, conversions
- **Bid Recommendations**: Sortable table with filters and CSV export
- **Top Keywords**: Rankings by ROAS, conversions, revenue, or clicks
- **What-If Calculator**: Simulate bid changes and estimate impact

## Prerequisites

- Python environment with uv
- BigQuery datasets populated with data (run dbt models first)
- Google Cloud authentication configured (`gcloud auth application-default login`)
- `.env` file with `GCP_PROJECT_ID` set

## Installation

Dependencies are managed via uv:

```bash
uv add streamlit plotly python-dotenv
```

## Running the Dashboard

```bash
streamlit run dashboards/app.py
```

Or with uv:

```bash
uv run streamlit run dashboards/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Data Sources

The dashboard queries the following BigQuery tables:

- `marts_marketing.fct_keyword_performance` - Daily keyword performance metrics
- `marts_marketing.fct_bid_recommendations` - Bid optimization recommendations
- `marts_analytics.keyword_roi_summary` - Aggregated keyword ROI metrics
- `marts_analytics.bid_optimization_candidates` - Filtered actionable recommendations

Ensure these tables exist and have data by running:

```bash
./scripts/dbt.sh run
./scripts/dbt.sh test
```

## Dashboard Tabs

### 📈 Overview
- KPI cards with current metrics
- ROAS trend over time
- Cost vs revenue comparison
- Click and conversion volume
- Campaign performance breakdown

### 🎯 Bid Recommendations
- Actionable bid recommendations with confidence scores
- Filters: bid action, confidence level, campaigns
- Expected impact calculations
- CSV export functionality

### 🏆 Top Keywords
- Leaderboard of best-performing keywords
- Rank by ROAS, conversions, revenue, or clicks
- Performance tier indicators

### 🧮 What-If Calculator
- Interactive scenario planning
- Simulate bid changes
- Estimate volume and revenue impact
- Simple elasticity model

## Configuration

Environment variables in `.env`:

```bash
GCP_PROJECT_ID=your-project-id
BQ_DATASET_MARTS_MARKETING=marts_marketing
BQ_DATASET_MARTS_ANALYTICS=marts_analytics
```

## Performance

- Data is cached for 5 minutes (`ttl=300`)
- Use the "Refresh Data" button in sidebar to clear cache
- Queries are limited to prevent long load times

## Troubleshooting

**Dashboard won't start:**
- Check dependencies: `uv run streamlit --version`
- Verify .env file exists and has GCP_PROJECT_ID

**No data showing:**
- Run dbt models: `uv run dbt run`
- Check BigQuery datasets exist
- Verify authentication: `gcloud auth application-default login`

**Permission errors:**
- Ensure your GCP user has BigQuery Data Viewer role
- Check project ID is correct in .env

## Next Steps

- Deploy to Streamlit Cloud for shared access
- Add more advanced filters (quality score, match type)
- Implement automated email reports
- Add anomaly detection alerts
