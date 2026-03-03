#!/usr/bin/env python3
"""Generate synthetic Google Ads data for development and testing.

This script generates realistic synthetic data based on patterns observed
in real Google Ads exports. See docs/DATA_REVIEW.md for specifications.

Usage:
    uv run scripts/generate_synthetic_data.py
    uv run scripts/generate_synthetic_data.py --config custom_config.yaml
    uv run scripts/generate_synthetic_data.py --output-dir data/custom
"""

import argparse
import hashlib
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from faker import Faker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """Generate synthetic Google Ads data matching real export patterns."""

    def __init__(self, config_path: str | Path):
        """Initialize generator with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.fake = Faker()

        # Set seeds for reproducibility
        seed = self.config["general"].get("seed", 42)
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

        # Parse dates
        self.start_date = datetime.strptime(
            self.config["general"]["start_date"], "%Y-%m-%d"
        )
        self.end_date = self.start_date + timedelta(
            days=self.config["general"]["date_range_days"]
        )

        # Storage for generated data
        self.campaigns = []
        self.ad_groups = []
        self.keywords = []
        self.search_terms = []
        self.auction_insights = []

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _weighted_choice(self, weights: dict) -> str:
        """Make a weighted random choice from a dictionary."""
        items = list(weights.keys())
        probs = list(weights.values())
        # Normalize probabilities
        total = sum(probs)
        probs = [p / total for p in probs]
        return np.random.choice(items, p=probs)

    def _generate_id(self, *args) -> str:
        """Generate a deterministic ID from input values."""
        content = "-".join(str(a) for a in args)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _apply_seasonality(self, base_value: float, date: datetime) -> float:
        """Apply seasonal and day-of-week multipliers to a value."""
        monthly = self.config["seasonality"]["monthly"]
        dow = self.config["seasonality"]["day_of_week"]

        month_mult = monthly.get(date.month, 1.0)
        dow_mult = dow.get(date.weekday(), 1.0)

        return base_value * month_mult * dow_mult

    def generate_campaigns(self) -> list[dict]:
        """Generate campaign structures."""
        logger.info("Generating campaigns...")
        markets = self.config["geography"]["markets"]
        campaign_types = self.config["campaigns"]["types"]
        type_weights = self.config["campaigns"]["type_weights"]

        campaigns = []
        for market in markets:
            for camp_type in campaign_types:
                campaign = {
                    "campaign_id": self._generate_id(market, camp_type),
                    "campaign_name": f"{market} - {camp_type} - Search",
                    "market": market,
                    "campaign_type": camp_type,
                    "type_weight": type_weights.get(camp_type, 0.05),
                }
                campaigns.append(campaign)

        self.campaigns = campaigns
        logger.info(f"Generated {len(campaigns)} campaigns")
        return campaigns

    def generate_ad_groups(self) -> list[dict]:
        """Generate ad groups for each campaign."""
        logger.info("Generating ad groups...")
        ad_group_config = self.config["ad_groups"]
        min_groups, max_groups = ad_group_config["per_campaign"]

        ad_groups = []
        for campaign in self.campaigns:
            camp_type = campaign["campaign_type"]
            themes = ad_group_config["themes"].get(camp_type, ["General"])
            num_groups = random.randint(min_groups, min(max_groups, len(themes)))
            selected_themes = random.sample(themes, num_groups)

            for theme in selected_themes:
                ad_group = {
                    "ad_group_id": self._generate_id(campaign["campaign_id"], theme),
                    "ad_group_name": theme,
                    "campaign_id": campaign["campaign_id"],
                    "campaign_name": campaign["campaign_name"],
                    "campaign_type": camp_type,
                    "market": campaign["market"],
                }
                ad_groups.append(ad_group)

        self.ad_groups = ad_groups
        logger.info(f"Generated {len(ad_groups)} ad groups")
        return ad_groups

    def generate_keywords(self) -> list[dict]:
        """Generate keywords for each ad group."""
        logger.info("Generating keywords...")
        kw_config = self.config["keywords"]
        min_kw, max_kw = kw_config["per_ad_group"]
        match_weights = kw_config["match_type_weights"]
        status_weights = kw_config["status_weights"]
        templates = kw_config["keyword_templates"]
        services = kw_config["services"]

        qs_config = self.config["quality_scores"]
        qs_dist = qs_config["distribution"]

        keywords = []
        for ad_group in self.ad_groups:
            camp_type = ad_group["campaign_type"]
            market = ad_group["market"]
            num_keywords = random.randint(min_kw, max_kw)

            kw_templates = templates.get(camp_type, templates["NonBrand"])

            for i in range(num_keywords):
                # Generate keyword text
                template = random.choice(kw_templates)
                service = random.choice(services)
                keyword_text = template.format(service=service, city=market.lower())

                # Generate attributes
                match_type = self._weighted_choice(match_weights)
                status = self._weighted_choice(status_weights)
                qs_raw = self._weighted_choice(qs_dist)
                quality_score = None if qs_raw == "--" else int(qs_raw)

                # Generate quality-related attributes
                exp_ctr = self._weighted_choice(qs_config["exp_ctr_weights"])
                landing_exp = self._weighted_choice(qs_config["landing_page_weights"])
                ad_relevance = self._weighted_choice(qs_config["ad_relevance_weights"])

                # Correlate quality attributes with QS
                if quality_score and quality_score >= 7:
                    exp_ctr = random.choice(["Above average", "Average"])
                    landing_exp = random.choice(["Above average", "Average"])
                elif quality_score and quality_score <= 3:
                    exp_ctr = random.choice(["Below average", "Average"])
                    landing_exp = random.choice(["Below average", "Average"])

                keyword = {
                    "keyword_id": self._generate_id(
                        ad_group["ad_group_id"], keyword_text, i
                    ),
                    "keyword": f'"""{keyword_text}"""',  # Triple-quoted like source
                    "keyword_clean": keyword_text,
                    "keyword_status": "Enabled" if status != "Paused" else "Paused",
                    "match_type": match_type,
                    "campaign": ad_group["campaign_name"],
                    "campaign_type": camp_type,
                    "ad_group": ad_group["ad_group_name"],
                    "status": status,
                    "status_reasons": "low quality" if status == "Limited" else "",
                    "quality_score": quality_score,
                    "exp_ctr": exp_ctr,
                    "landing_page_exp": landing_exp,
                    "ad_relevance": ad_relevance,
                    "market": market,
                }
                keywords.append(keyword)

        self.keywords = keywords
        logger.info(f"Generated {len(keywords)} keywords")
        return keywords

    def generate_keyword_performance(self) -> pd.DataFrame:
        """Generate daily performance data for keywords."""
        logger.info("Generating keyword performance data...")
        perf_config = self.config["performance"]
        type_mods = perf_config["type_modifiers"]
        qs_cpc_mods = perf_config["qs_cpc_modifier"]

        records = []
        current_date = self.start_date
        total_days = self.config["general"]["date_range_days"]

        while current_date <= self.end_date:
            for keyword in self.keywords:
                # Skip paused keywords most of the time
                if keyword["keyword_status"] == "Paused" and random.random() > 0.1:
                    continue

                camp_type = keyword["campaign_type"]
                type_mod = type_mods.get(camp_type, {})
                qs = keyword["quality_score"]

                # Base impressions with seasonality
                base_impr = np.random.lognormal(
                    mean=np.log(perf_config["impressions"]["mean"]),
                    sigma=0.8,
                )
                impressions = int(
                    self._apply_seasonality(base_impr, current_date)
                    * type_mod.get("ctr_modifier", 1.0)
                )
                impressions = max(0, min(impressions, 1000))

                # Skip if no impressions
                if impressions == 0:
                    continue

                # CTR based on quality score and campaign type
                base_ctr = np.random.normal(
                    perf_config["ctr"]["mean"],
                    perf_config["ctr"]["std"],
                )
                ctr = base_ctr * type_mod.get("ctr_modifier", 1.0)
                if qs:
                    ctr *= qs / 5  # Higher QS = higher CTR
                ctr = max(0.005, min(ctr, 0.30))

                clicks = int(impressions * ctr)

                # CPC based on quality score
                base_cpc = np.random.lognormal(
                    mean=np.log(perf_config["cpc"]["mean"]),
                    sigma=0.5,
                )
                cpc = base_cpc * type_mod.get("cpc_modifier", 1.0)
                if qs:
                    cpc *= qs_cpc_mods.get(qs, 1.0)
                cpc = max(
                    perf_config["cpc"]["min"], min(cpc, perf_config["cpc"]["max"])
                )

                cost = clicks * cpc

                # Conversions
                base_conv_rate = np.random.normal(
                    perf_config["conversion_rate"]["mean"],
                    perf_config["conversion_rate"]["std"],
                )
                conv_rate = base_conv_rate * type_mod.get("conv_modifier", 1.0)
                if qs:
                    conv_rate *= qs / 5
                conv_rate = max(0, min(conv_rate, 0.20))
                conversions = np.random.binomial(clicks, conv_rate)

                # Conversion value (average $2000-5000 for bathroom remodels)
                conv_value = conversions * np.random.uniform(2000, 5000)

                # Impression share metrics
                impr_share = np.random.uniform(0.30, 0.80)
                impr_top_pct = np.random.uniform(0.50, 0.90)
                impr_abs_top_pct = np.random.uniform(0.30, 0.70)

                # Max CPC (bid)
                max_cpc = cpc * np.random.uniform(1.1, 1.5)

                record = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "keyword_id": keyword["keyword_id"],
                    "keyword_status": keyword["keyword_status"],
                    "keyword": keyword["keyword"],
                    "match_type": keyword["match_type"],
                    "campaign": keyword["campaign"],
                    "ad_group": keyword["ad_group"],
                    "status": keyword["status"],
                    "status_reasons": keyword["status_reasons"],
                    "currency_code": "USD",
                    "max_cpc": f"{max_cpc:.2f}" if max_cpc else "--",
                    "clicks": clicks,
                    "cost": f"{cost:.2f}",
                    "impressions": impressions,
                    "est_first_page_bid": f"{cpc * 0.8:.2f}",
                    "est_top_of_page_bid": f"{cpc * 1.0:.2f}",
                    "est_first_position_bid": f"{cpc * 1.2:.2f}",
                    "search_impr_share": f"{impr_share * 100:.2f}%",
                    "impr_top_pct": f"{impr_top_pct * 100:.2f}%",
                    "impr_abs_top_pct": f"{impr_abs_top_pct * 100:.2f}%",
                    "conversions": conversions,
                    "quality_score": (
                        keyword["quality_score"] if keyword["quality_score"] else "--"
                    ),
                    "exp_ctr": keyword["exp_ctr"],
                    "landing_page_exp": keyword["landing_page_exp"],
                    "ad_relevance": keyword["ad_relevance"],
                    "conv_value": f"{conv_value:.2f}",
                }
                records.append(record)

            current_date += timedelta(days=1)
            if (current_date - self.start_date).days % 30 == 0:
                logger.info(
                    f"Progress: {(current_date - self.start_date).days}/{total_days} days"
                )

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} keyword performance records")
        return df

    def generate_search_terms(self, keyword_df: pd.DataFrame) -> pd.DataFrame:
        """Generate search term data based on keywords."""
        logger.info("Generating search terms...")
        st_config = self.config["search_terms"]
        min_ratio, max_ratio = st_config["per_keyword_ratio"]

        # Pre-compute keyword statistics for efficiency
        logger.info("Pre-computing keyword statistics...")
        kw_stats = (
            keyword_df.groupby("keyword_id")
            .agg(
                {
                    "clicks": "sum",
                    "cost": lambda x: sum(float(str(v).replace(",", "")) for v in x),
                    "keyword": "first",
                    "match_type": "first",
                    "campaign": "first",
                    "ad_group": "first",
                }
            )
            .reset_index()
        )

        records = []
        total_keywords = len(kw_stats)

        for idx, kw_row in kw_stats.iterrows():
            if idx % 500 == 0:
                logger.info(f"Search terms progress: {idx}/{total_keywords} keywords")

            num_terms = random.randint(min_ratio, max_ratio)
            keyword_text = str(kw_row["keyword"]).strip('"')
            total_clicks = kw_row["clicks"]
            total_cost = kw_row["cost"]
            avg_cpc = total_cost / max(1, total_clicks) if total_clicks > 0 else 50.0

            for i in range(num_terms):
                # Generate search term variation
                if random.random() < st_config["close_variant_rate"]:
                    search_term = self._generate_close_variant(keyword_text)
                    match_type = f"{kw_row['match_type']} (close variant)"
                else:
                    search_term = keyword_text
                    match_type = kw_row["match_type"]

                # Determine if added/excluded
                added_excluded = self._weighted_choice(
                    st_config["added_excluded_weights"]
                )

                # Performance (proportional to keyword performance)
                if total_clicks > 0:
                    # Distribute clicks across search terms (power law)
                    term_clicks = int(total_clicks * np.random.power(0.5) / num_terms)
                    term_clicks = max(0, term_clicks)
                else:
                    term_clicks = 0

                # Calculate other metrics based on clicks
                if term_clicks > 0:
                    term_cost = term_clicks * avg_cpc * np.random.uniform(0.8, 1.2)
                    term_impressions = int(term_clicks / 0.10)  # ~10% CTR
                    term_conversions = np.random.binomial(term_clicks, 0.05)
                    term_conv_value = term_conversions * np.random.uniform(2000, 5000)
                else:
                    term_cost = 0
                    term_impressions = random.randint(0, 5)
                    term_conversions = 0
                    term_conv_value = 0

                record = {
                    "search_term": search_term,
                    "match_type": match_type,
                    "added_excluded": added_excluded,
                    "campaign": kw_row["campaign"],
                    "ad_group": kw_row["ad_group"],
                    "keyword": kw_row["keyword"],
                    "clicks": term_clicks,
                    "currency_code": "USD",
                    "cost": f"{term_cost:.2f}",
                    "impressions": term_impressions,
                    "impr_top_pct": (
                        f"{np.random.uniform(50, 90):.2f}%"
                        if term_impressions > 0
                        else "--"
                    ),
                    "impr_abs_top_pct": (
                        f"{np.random.uniform(30, 70):.2f}%"
                        if term_impressions > 0
                        else "--"
                    ),
                    "conversions": term_conversions,
                    "leads": term_conversions,  # Assume leads = conversions
                    "conv_value": f"{term_conv_value:.2f}",
                }
                records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} search term records")
        return df

    def _generate_close_variant(self, keyword: str) -> str:
        """Generate a close variant of a keyword."""
        variations = [
            lambda k: k + "s",  # Plural
            lambda k: k.replace(" ", ""),  # No spaces
            lambda k: k + " near me",
            lambda k: k + " services",
            lambda k: "best " + k,
            lambda k: k + " company",
            lambda k: k + " cost",
            lambda k: k + " price",
            lambda k: k + " reviews",
            lambda k: "local " + k,
            lambda k: k + " contractors",
            lambda k: k + " estimate",
            lambda k: "how much " + k,
        ]
        variant_fn = random.choice(variations)
        return variant_fn(keyword)

    def generate_auction_insights(self) -> pd.DataFrame:
        """Generate auction insights data."""
        logger.info("Generating auction insights...")
        comp_config = self.config["competitors"]
        competitors = comp_config["domains"]

        records = []
        current_date = self.start_date

        # Generate monthly data
        while current_date <= self.end_date:
            month_str = current_date.strftime("%B %Y")

            # Your company's metrics
            your_impr_share = np.random.uniform(
                comp_config["your_impression_share"]["min"],
                comp_config["your_impression_share"]["max"],
            )

            record = {
                "month": month_str,
                "display_url_domain": "You",
                "impression_share": f"{your_impr_share * 100:.2f}%",
                "overlap_rate": "--",
                "position_above_rate": "--",
                "top_of_page_rate": f"{np.random.uniform(70, 85):.2f}%",
                "abs_top_of_page_rate": f"{np.random.uniform(45, 65):.2f}%",
                "outranking_share": "--",
            }
            records.append(record)

            # Competitor metrics
            for competitor in competitors:
                comp_impr_share = np.random.uniform(
                    comp_config["competitor_impression_share"]["min"],
                    comp_config["competitor_impression_share"]["max"],
                )

                # Some metrics may be unavailable
                overlap = (
                    f"{np.random.uniform(10, 30):.2f}%"
                    if random.random() > 0.2
                    else "--"
                )
                position_above = (
                    f"{np.random.uniform(40, 60):.2f}%"
                    if random.random() > 0.3
                    else "--"
                )
                outranking = (
                    f"{np.random.uniform(45, 65):.2f}%"
                    if random.random() > 0.2
                    else "--"
                )

                # Low impression share shows as "< 10%"
                if comp_impr_share < 0.10:
                    impr_share_str = "< 10%"
                else:
                    impr_share_str = f"{comp_impr_share * 100:.2f}%"

                record = {
                    "month": month_str,
                    "display_url_domain": competitor,
                    "impression_share": impr_share_str,
                    "overlap_rate": overlap,
                    "position_above_rate": position_above,
                    "top_of_page_rate": f"{np.random.uniform(50, 75):.2f}%",
                    "abs_top_of_page_rate": f"{np.random.uniform(25, 50):.2f}%",
                    "outranking_share": outranking,
                }
                records.append(record)

            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} auction insight records")
        return df

    def save_data(
        self,
        keyword_df: pd.DataFrame,
        search_term_df: pd.DataFrame,
        auction_df: pd.DataFrame,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        """Save generated data to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        delimiter = self.config["general"]["delimiter"]
        encoding = self.config["general"]["encoding"]

        # Date range for headers
        date_range = f'"{self.start_date.strftime("%B %d, %Y")} - {self.end_date.strftime("%B %d, %Y")}"'

        output_files = {}

        # Save keywords
        kw_path = output_dir / "Search_keywords-Synthetic.csv"
        with open(kw_path, "w", encoding=encoding) as f:
            f.write("Search keyword report\n")
            f.write(f"{date_range}\n")
        keyword_df.to_csv(
            kw_path, mode="a", sep=delimiter, index=False, encoding=encoding
        )
        output_files["keywords"] = kw_path
        logger.info(f"Saved keywords to {kw_path}")

        # Save search terms
        st_path = output_dir / "Search_terms-Synthetic.csv"
        with open(st_path, "w", encoding=encoding) as f:
            f.write("Search terms report\n")
            f.write(f"{date_range}\n")
        search_term_df.to_csv(
            st_path, mode="a", sep=delimiter, index=False, encoding=encoding
        )
        output_files["search_terms"] = st_path
        logger.info(f"Saved search terms to {st_path}")

        # Save auction insights
        ai_path = output_dir / "Auction_Insights-Synthetic.csv"
        with open(ai_path, "w", encoding=encoding) as f:
            f.write("Auction insights report\n")
            f.write(f"{date_range}\n")
        auction_df.to_csv(
            ai_path, mode="a", sep=delimiter, index=False, encoding=encoding
        )
        output_files["auction_insights"] = ai_path
        logger.info(f"Saved auction insights to {ai_path}")

        return output_files

    def generate_all(self, output_dir: str | Path | None = None) -> dict[str, Path]:
        """Generate all synthetic data."""
        logger.info("Starting synthetic data generation...")
        start_time = datetime.now()

        # Generate structures
        self.generate_campaigns()
        self.generate_ad_groups()
        self.generate_keywords()

        # Generate performance data
        keyword_df = self.generate_keyword_performance()
        search_term_df = self.generate_search_terms(keyword_df)
        auction_df = self.generate_auction_insights()

        # Save data
        if output_dir is None:
            output_dir = self.config["general"]["output_dir"]
        output_files = self.save_data(
            keyword_df, search_term_df, auction_df, output_dir
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Generation complete in {elapsed:.1f} seconds")

        # Print summary
        logger.info("Summary:")
        logger.info(f"  Campaigns: {len(self.campaigns)}")
        logger.info(f"  Ad Groups: {len(self.ad_groups)}")
        logger.info(f"  Keywords: {len(self.keywords)}")
        logger.info(f"  Keyword Performance Records: {len(keyword_df)}")
        logger.info(f"  Search Terms: {len(search_term_df)}")
        logger.info(f"  Auction Insights: {len(auction_df)}")

        return output_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate synthetic Google Ads data")
    parser.add_argument(
        "--config",
        type=str,
        default="scripts/synthetic_data_config.yaml",
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (overrides config)",
    )
    args = parser.parse_args()

    # Find config relative to script or absolute
    config_path = Path(args.config)
    if not config_path.is_absolute():
        # Try relative to current dir, then relative to script
        if not config_path.exists():
            script_dir = Path(__file__).parent
            config_path = script_dir / args.config.replace("scripts/", "")

    if not config_path.exists():
        logger.error(f"Config file not found: {args.config}")
        return 1

    generator = SyntheticDataGenerator(config_path)
    generator.generate_all(output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    exit(main())
