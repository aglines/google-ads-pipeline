"""
Streamlit Dashboard for Google Ads Bid Optimization
Displays KPIs, trends, and bid recommendations from BigQuery marts.
"""

import os
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_MARKETING = os.getenv("BQ_DATASET_MARTS_MARKETING", "marts_marketing")
DATASET_ANALYTICS = os.getenv("BQ_DATASET_MARTS_ANALYTICS", "marts_analytics")


# BigQuery client
@st.cache_resource
def get_bigquery_client():
    """Initialize BigQuery client with ADC authentication."""
    return bigquery.Client(project=PROJECT_ID)


# Data loading functions
@st.cache_data(ttl=300)
def load_kpi_summary() -> Dict:
    """Load overall KPI metrics."""
    client = get_bigquery_client()

    query = f"""
    SELECT
        SUM(total_impressions) as impressions,
        SUM(total_clicks) as clicks,
        SUM(total_cost) as cost,
        SUM(total_conversions) as conversions,
        SUM(total_conversion_value) as conversion_value,
        SAFE_DIVIDE(SUM(total_clicks), SUM(total_impressions)) as ctr,
        SAFE_DIVIDE(SUM(total_cost), SUM(total_clicks)) as cpc,
        SAFE_DIVIDE(SUM(total_conversions), SUM(total_clicks)) as conversion_rate,
        SAFE_DIVIDE(SUM(total_conversion_value), SUM(total_cost)) as roas,
        MAX(currency_code) as currency
    FROM `{PROJECT_ID}.{DATASET_ANALYTICS}.keyword_roi_summary`
    """

    df = client.query(query).to_dataframe()
    return df.iloc[0].to_dict() if not df.empty else {}


@st.cache_data(ttl=300)
def load_performance_trend(start_date: str, end_date: str) -> pd.DataFrame:
    """Load daily performance trend."""
    client = get_bigquery_client()

    query = f"""
    SELECT
        date_key as date,
        SUM(impressions) as impressions,
        SUM(clicks) as clicks,
        SUM(cost) as cost,
        SUM(conversions) as conversions,
        SUM(conversion_value) as conversion_value,
        SAFE_DIVIDE(SUM(conversion_value), SUM(cost)) as roas
    FROM `{PROJECT_ID}.{DATASET_MARKETING}.fct_keyword_performance`
    WHERE date_key BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY date_key
    ORDER BY date_key
    """

    return client.query(query).to_dataframe()


@st.cache_data(ttl=300)
def load_campaign_performance() -> pd.DataFrame:
    """Load campaign-level performance."""
    client = get_bigquery_client()

    query = f"""
    SELECT
        campaign_name,
        SUM(total_impressions) as impressions,
        SUM(total_clicks) as clicks,
        SUM(total_cost) as cost,
        SUM(total_conversions) as conversions,
        SAFE_DIVIDE(SUM(total_conversion_value), SUM(total_cost)) as roas,
        roi_tier,
        volume_tier
    FROM `{PROJECT_ID}.{DATASET_ANALYTICS}.keyword_roi_summary`
    GROUP BY campaign_name, roi_tier, volume_tier
    ORDER BY cost DESC
    LIMIT 20
    """

    return client.query(query).to_dataframe()


@st.cache_data(ttl=300)
def load_bid_recommendations(min_confidence: int = 0) -> pd.DataFrame:
    """Load bid optimization recommendations."""
    client = get_bigquery_client()

    query = f"""
    SELECT
        keyword,
        match_type,
        campaign_name,
        ad_group_name,
        current_bid,
        suggested_bid,
        bid_action,
        ROUND(bid_change_amount, 2) as bid_change_amount,
        ROUND((suggested_bid - current_bid) / current_bid * 100, 1) as bid_change_pct,
        ROUND(roas_7d_avg, 2) as roas_7d,
        ROUND(ctr_7d_avg * 100, 2) as ctr_7d_pct,
        ROUND(conversion_rate_7d_avg * 100, 2) as conv_rate_7d_pct,
        quality_score,
        confidence_score,
        ROUND(expected_weekly_impact, 2) as expected_impact,
        recommendation_rationale,
        action_priority,
        currency_code
    FROM `{PROJECT_ID}.{DATASET_ANALYTICS}.bid_optimization_candidates`
    WHERE confidence_score >= {min_confidence}
    ORDER BY action_priority, ABS(expected_impact) DESC
    LIMIT 100
    """

    return client.query(query).to_dataframe()


@st.cache_data(ttl=300)
def load_top_keywords(metric: str = "roas", limit: int = 20) -> pd.DataFrame:
    """Load top performing keywords by metric."""
    client = get_bigquery_client()

    metric_col_map = {
        "roas": "overall_roas",
        "conversions": "total_conversions",
        "revenue": "total_conversion_value",
        "clicks": "total_clicks",
    }

    order_col = metric_col_map.get(metric, "overall_roas")

    query = f"""
    SELECT
        keyword,
        match_type,
        campaign_name,
        total_impressions,
        total_clicks,
        total_cost,
        total_conversions,
        ROUND(overall_roas, 2) as roas,
        ROUND(overall_ctr * 100, 2) as ctr_pct,
        ROUND(overall_conversion_rate * 100, 2) as conv_rate_pct,
        roi_tier
    FROM `{PROJECT_ID}.{DATASET_ANALYTICS}.keyword_roi_summary`
    WHERE total_impressions > 100
    ORDER BY {order_col} DESC
    LIMIT {limit}
    """

    return client.query(query).to_dataframe()


# UI Components
def display_kpi_cards(kpis: Dict):
    """Display KPI summary cards."""
    currency = kpis.get("currency", "USD")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Impressions",
            f"{kpis.get('impressions', 0):,.0f}",
            help="Total ad impressions",
        )

    with col2:
        st.metric(
            "Total Clicks",
            f"{kpis.get('clicks', 0):,.0f}",
            delta=f"{kpis.get('ctr', 0)*100:.2f}% CTR",
            help="Total clicks and click-through rate",
        )

    with col3:
        st.metric(
            "Total Cost",
            f"{currency} {kpis.get('cost', 0):,.2f}",
            delta=f"{currency}{kpis.get('cpc', 0):.2f} CPC",
            help="Total ad spend and cost per click",
        )

    with col4:
        st.metric(
            "Total Conversions",
            f"{kpis.get('conversions', 0):,.0f}",
            delta=f"{kpis.get('roas', 0):.2f}x ROAS",
            help="Total conversions and return on ad spend",
        )

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            "Conv. Rate",
            f"{kpis.get('conversion_rate', 0)*100:.2f}%",
            help="Conversion rate (conversions / clicks)",
        )

    with col6:
        st.metric(
            "Revenue",
            f"{currency} {kpis.get('conversion_value', 0):,.2f}",
            help="Total conversion value",
        )


def plot_performance_trend(df: pd.DataFrame):
    """Plot time series of key metrics."""
    if df.empty:
        st.warning("No performance data available for selected date range")
        return

    # ROAS trend
    fig_roas = px.line(
        df,
        x="date",
        y="roas",
        title="ROAS Trend",
        labels={"roas": "ROAS", "date": "Date"},
    )
    fig_roas.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="red",
        annotation_text="Break-even",
        annotation_position="right",
    )
    st.plotly_chart(fig_roas, use_container_width=True)

    # Cost and Revenue trend
    fig_cost_rev = go.Figure()
    fig_cost_rev.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["cost"],
            name="Cost",
            mode="lines",
            line=dict(color="red"),
        )
    )
    fig_cost_rev.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["conversion_value"],
            name="Revenue",
            mode="lines",
            line=dict(color="green"),
        )
    )
    fig_cost_rev.update_layout(
        title="Cost vs Revenue",
        xaxis_title="Date",
        yaxis_title="Amount",
        hovermode="x unified",
    )
    st.plotly_chart(fig_cost_rev, use_container_width=True)

    # Clicks and Conversions
    fig_volume = go.Figure()
    fig_volume.add_trace(
        go.Bar(x=df["date"], y=df["clicks"], name="Clicks", marker_color="lightblue")
    )
    fig_volume.add_trace(
        go.Bar(
            x=df["date"],
            y=df["conversions"],
            name="Conversions",
            marker_color="darkblue",
        )
    )
    fig_volume.update_layout(
        title="Clicks and Conversions",
        xaxis_title="Date",
        yaxis_title="Count",
        barmode="group",
    )
    st.plotly_chart(fig_volume, use_container_width=True)


def display_bid_recommendations(df: pd.DataFrame):
    """Display bid recommendations table with filtering and export."""
    if df.empty:
        st.warning("No bid recommendations available")
        return

    st.subheader(f"Bid Recommendations ({len(df)} total)")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        action_filter = st.multiselect(
            "Bid Action",
            options=df["bid_action"].unique().tolist(),
            default=df["bid_action"].unique().tolist(),
        )

    with col2:
        conf_min = int(df["confidence_score"].min())
        conf_max = int(df["confidence_score"].max())

        # Handle case where all confidence scores are the same
        if conf_min == conf_max:
            st.info(f"All recommendations have confidence score: {conf_min}")
            min_conf = conf_min
        else:
            min_conf = st.slider(
                "Min Confidence Score",
                min_value=conf_min,
                max_value=conf_max,
                value=conf_min,
            )

    with col3:
        campaigns = st.multiselect(
            "Campaigns",
            options=df["campaign_name"].unique().tolist(),
            default=df["campaign_name"].unique().tolist(),
        )

    # Apply filters
    filtered_df = df[
        (df["bid_action"].isin(action_filter))
        & (df["confidence_score"] >= min_conf)
        & (df["campaign_name"].isin(campaigns))
    ]

    st.dataframe(filtered_df, use_container_width=True, height=400)

    # Export button
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"bid_recommendations_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Increase Actions",
            len(filtered_df[filtered_df["bid_action"] == "INCREASE"]),
        )
    with col2:
        st.metric(
            "Decrease Actions",
            len(filtered_df[filtered_df["bid_action"] == "DECREASE"]),
        )
    with col3:
        total_impact = filtered_df["expected_impact"].sum()
        st.metric("Total Expected Impact", f"{total_impact:,.2f}")


def what_if_calculator():
    """Interactive what-if scenario calculator for bid changes."""
    st.subheader("What-If Scenario Calculator")

    col1, col2 = st.columns(2)

    with col1:
        current_bid = st.number_input(
            "Current Bid ($)", min_value=0.10, value=1.50, step=0.10
        )
        current_clicks = st.number_input(
            "Current Weekly Clicks", min_value=0, value=100, step=10
        )
        current_conversions = st.number_input(
            "Current Weekly Conversions", min_value=0, value=5, step=1
        )
        current_roas = st.number_input(
            "Current ROAS", min_value=0.0, value=2.5, step=0.1
        )

    with col2:
        bid_change_pct = st.slider(
            "Bid Change (%)", min_value=-50, max_value=50, value=0, step=5
        )

        # Calculate new metrics (simplified model)
        new_bid = current_bid * (1 + bid_change_pct / 100)

        # Estimate click volume change (elastic response)
        click_elasticity = 0.3  # 30% volume change per 10% bid change
        new_clicks = current_clicks * (1 + (bid_change_pct / 100) * click_elasticity)

        # Assume conversion rate stays relatively stable
        new_conversions = current_conversions * (new_clicks / current_clicks)

        # New cost
        new_cost = new_bid * new_clicks
        old_cost = current_bid * current_clicks

        # New revenue (assuming same ROAS initially)
        new_revenue = new_cost * current_roas

        st.metric("New Bid", f"${new_bid:.2f}", delta=f"{bid_change_pct:+d}%")
        st.metric(
            "Projected Clicks",
            f"{new_clicks:.0f}",
            delta=f"{new_clicks - current_clicks:+.0f}",
        )
        st.metric(
            "Projected Conversions",
            f"{new_conversions:.0f}",
            delta=f"{new_conversions - current_conversions:+.0f}",
        )
        st.metric(
            "Projected Weekly Cost",
            f"${new_cost:.2f}",
            delta=f"${new_cost - old_cost:+.2f}",
        )
        st.metric(
            "Projected Revenue",
            f"${new_revenue:.2f}",
            delta=f"${new_revenue - (old_cost * current_roas):+.2f}",
        )

    st.info(
        "Note: This is a simplified model. Actual results may vary based on competition, quality score, and search volume."
    )


# Main App
def main():
    st.set_page_config(
        page_title="Google Ads Bid Optimizer", page_icon="📊", layout="wide"
    )

    st.title("📊 Google Ads Bid Optimization Dashboard")
    st.markdown("Real-time insights and bid recommendations from BigQuery")

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")

        # Date range selector
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        date_range = st.date_input(
            "Date Range", value=(start_date, end_date), max_value=end_date
        )

        if len(date_range) == 2:
            start_date_str = date_range[0].strftime("%Y-%m-%d")
            end_date_str = date_range[1].strftime("%Y-%m-%d")
        else:
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

        st.divider()

        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📈 Overview",
            "🎯 Bid Recommendations",
            "🏆 Top Keywords",
            "🧮 What-If Calculator",
        ]
    )

    with tab1:
        st.header("Performance Overview")

        # Load and display KPIs
        with st.spinner("Loading KPIs..."):
            kpis = load_kpi_summary()
            display_kpi_cards(kpis)

        st.divider()

        # Performance trends
        with st.spinner("Loading performance trends..."):
            trend_df = load_performance_trend(start_date_str, end_date_str)
            plot_performance_trend(trend_df)

        st.divider()

        # Campaign performance
        st.subheader("Campaign Performance")
        with st.spinner("Loading campaign data..."):
            campaign_df = load_campaign_performance()
            if not campaign_df.empty:
                st.dataframe(campaign_df, use_container_width=True)

                # Campaign ROAS chart
                fig = px.bar(
                    campaign_df.head(10),
                    x="campaign_name",
                    y="roas",
                    color="roi_tier",
                    title="Top 10 Campaigns by ROAS",
                    labels={"roas": "ROAS", "campaign_name": "Campaign"},
                )
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("Bid Recommendations")

        with st.spinner("Loading recommendations..."):
            rec_df = load_bid_recommendations()
            display_bid_recommendations(rec_df)

    with tab3:
        st.header("Top Performing Keywords")

        col1, col2 = st.columns([1, 3])

        with col1:
            metric_choice = st.selectbox(
                "Rank by",
                options=["roas", "conversions", "revenue", "clicks"],
                format_func=lambda x: x.upper() if x == "roas" else x.title(),
            )

            limit = st.slider(
                "Number of keywords", min_value=10, max_value=50, value=20
            )

        with col2:
            with st.spinner("Loading top keywords..."):
                top_keywords = load_top_keywords(metric_choice, limit)
                if not top_keywords.empty:
                    st.dataframe(top_keywords, use_container_width=True)

    with tab4:
        what_if_calculator()

    # Footer
    st.divider()
    st.caption(
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data from BigQuery"
    )


if __name__ == "__main__":
    main()
