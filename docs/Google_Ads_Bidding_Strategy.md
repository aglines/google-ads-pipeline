# Google Ads Bidding Strategy Framework

## Overview
**Purpose**: Data-driven bidding optimization for Google Ads campaigns using historical performance, competitive intelligence, and search query analysis.

**Data Sources**:
- Search Keywords Report (bidded keywords performance)
- Search Terms Report (actual user queries)
- Auction Insights Report (competitive landscape)

**Goal**: Maximize ROI by adjusting bids based on performance signals, competitive pressure, and user intent indicators.

---

## Data Structure

### Input Datasets

**1. Search Keywords**
- Granularity: Keyword-level performance
- Metrics: Clicks, impressions, cost, conversions, CTR, CPC
- Dimensions: Campaign, ad group, match type, status
- Frequency: Daily/weekly updates

**2. Search Terms**
- Granularity: User query-level
- Metrics: Clicks, impressions, cost, conversions
- Dimensions: Campaign, ad group, triggering keyword, match type variant
- Frequency: Daily/weekly updates
- **Critical Use**: Discover what users actually search vs what you bid on

**3. Auction Insights**
- Granularity: Monthly competitor benchmarks
- Metrics: Impression share, overlap rate, position above rate, top of page rate
- Dimensions: Competitor domain, month
- Frequency: Monthly snapshots
- **Critical Use**: Understand competitive dynamics

---

## Bidding Strategy Components

### 1. Performance-Based Bid Adjustments

**Increase Bids (+10-30%) When**:
- Conversion rate > campaign average AND impression share < 70%
- CTR > 5% AND position < 3
- Cost per conversion < target CPA
- High-value conversions (tracked via conversion value)

**Decrease Bids (-10-30%) When**:
- Zero conversions after $100+ spend
- CTR < 1% (indicates poor ad relevance)
- CPA > 2x target
- Impression share > 90% (diminishing returns)

**Pause Keywords When**:
- Zero conversions after $200+ spend
- CTR < 0.5% consistently
- Only generating irrelevant search terms

### 2. Competitive Intelligence

**Monitor Auction Insights for**:
- **Impression Share Trends**: If your share drops >10% month-over-month, competitors are increasing spend
- **Overlap Rate**: High overlap (>50%) with specific competitor means direct competition for same queries
- **Position Above Rate**: If competitor consistently outranks you, consider bid increase or quality score improvement
- **Top of Page Rate**: Aim for >70% to maintain visibility

**Bid Adjustments Based on Competition**:
- Losing share to 1-2 specific competitors: Target +15-25% bid increase
- Dominating market (>60% impression share): Reduce bids slightly, monitor for share loss
- New competitor enters (appears in auction insights): Analyze their domains/strategy

### 3. Search Query Mining

**Keyword Discovery Process**:
1. Identify search terms with conversions that aren't exact match to existing keywords
2. Check if search term has sufficient volume (>10 searches/month)
3. Add as new keyword with appropriate match type
4. Monitor for 30 days, adjust bids based on performance

**Negative Keyword Identification**:
- Search terms with >$50 spend, zero conversions
- Irrelevant queries (e.g., "free", "DIY", "how to" if selling services)
- Broad match variants triggering unrelated searches

**Match Type Strategy**:
- **Exact Match**: High-intent, proven converters. Bid aggressively.
- **Phrase Match**: Moderate intent, balance between reach and relevance. Bid moderately.
- **Broad Match**: Discovery mode, tight negative keyword control. Bid conservatively.

### 4. Time-Based Patterns

**Day of Week**:
- Analyze conversion rate by day
- Increase bids on high-converting days (e.g., weekdays for B2B)
- Decrease bids on low-performing days (e.g., weekends if relevant)

**Hour of Day**:
- Identify peak conversion hours
- Implement dayparting bid adjustments (+20-40% during peak hours)

### 5. Geographic Performance

**If data available**:
- Compare CPA by metro area or state
- Increase bids in high-performing geos
- Exclude or reduce bids in consistently unprofitable areas

---

## Bid Calculation Framework

### Basic Bid Formula
```
New Bid = Base Bid × Performance Multiplier × Competitive Multiplier × Intent Multiplier
```

**Performance Multiplier**:
- Conversion Rate vs. Benchmark: If 2x benchmark → 1.3x multiplier
- CPA vs. Target: If 50% below target → 1.2x multiplier
- CTR vs. Benchmark: If 2x benchmark → 1.1x multiplier

**Competitive Multiplier**:
- Impression Share < 50%: 1.2x
- Impression Share 50-70%: 1.1x
- Impression Share > 80%: 0.9x
- Position Above Rate > 60%: 1.15x

**Intent Multiplier**:
- Exact match search term: 1.2x
- Phrase match variant: 1.0x
- Broad match variant: 0.8x

### Example Calculation
```
Keyword: "bathroom remodel houston"
Base Bid: $5.00
Conversion Rate: 8% (campaign avg: 4%) → 1.3x
Impression Share: 45% → 1.2x
Search Term Match: Exact → 1.2x

New Bid = $5.00 × 1.3 × 1.2 × 1.2 = $9.36
```

---

## Data Pipeline Architecture

### ETL Process

**Daily Ingestion**:
1. Pull Google Ads API data for keywords and search terms
2. Extract performance metrics (clicks, cost, conversions)
3. Load into BigQuery staging tables

**Weekly Aggregation**:
1. Calculate 7-day rolling averages for stability
2. Compute benchmark metrics (avg CTR, avg CPA by campaign)
3. Join search terms to keywords to analyze query quality

**Monthly Competitive Analysis**:
1. Ingest Auction Insights reports
2. Calculate month-over-month impression share changes
3. Identify competitive threats and opportunities

### Key SQL Queries

**High-Performing Keywords to Increase Bids**:
```sql
SELECT keyword, campaign, clicks, conversions, cost,
       cost/conversions AS cpa,
       conversions/clicks AS cvr
FROM keywords
WHERE conversions > 0
  AND cost/conversions < target_cpa
  AND impression_share < 0.70
ORDER BY conversions DESC
```

**Search Terms to Add as New Keywords**:
```sql
SELECT search_term, SUM(conversions) AS total_conv,
       SUM(cost) AS total_cost
FROM search_terms
WHERE search_term NOT IN (SELECT keyword FROM keywords)
GROUP BY search_term
HAVING total_conv > 0 AND total_cost > 50
ORDER BY total_conv DESC
```

**Negative Keyword Candidates**:
```sql
SELECT search_term, SUM(cost) AS wasted_spend,
       SUM(clicks) AS clicks
FROM search_terms
WHERE conversions = 0
GROUP BY search_term
HAVING SUM(cost) > 50
ORDER BY wasted_spend DESC
```

---

## Performance Monitoring

### KPIs to Track

**Primary Metrics**:
- **ROAS** (Return on Ad Spend): Target 4:1 minimum
- **CPA** (Cost Per Acquisition): Track by campaign, ad group, keyword
- **Conversion Rate**: Benchmark and trend analysis
- **Impression Share**: Maintain >60% for core keywords

**Secondary Metrics**:
- **Quality Score**: Aim for 7+ (affects CPC and ad rank)
- **Click-Through Rate**: Indicator of ad relevance
- **Average Position**: Track trends, not absolute numbers
- **Search Impression Share Lost (Budget)**: Indicates need for budget increase
- **Search Impression Share Lost (Rank)**: Indicates need for bid/quality improvements

### Alert Thresholds

**Immediate Action**:
- CPA increases >50% week-over-week
- Impression share drops >20% for top keywords
- New competitor appears with >30% overlap rate

**Review Within 24 Hours**:
- CTR drops below 2% for exact match keywords
- Zero conversions for 3+ days on previously converting keywords
- Budget pacing >120% of monthly target

---

## Advanced Strategies

### A/B Testing Framework
- Test bid changes on 20% of traffic first
- Run for minimum 2 weeks or 100 clicks
- Compare conversion rate and CPA before rollout

### Seasonal Adjustments
- Historical data shows Q4 performance patterns
- Pre-emptively adjust bids based on seasonal trends
- Budget allocation shifts for peak periods

### Competitor Response Strategy
- If competitor increases bids aggressively, don't always match
- Focus on quality score improvements for lower CPC
- Target long-tail keywords competitors may ignore

### Budget Optimization
- Reallocate budget from low ROAS campaigns to high performers
- Pause campaigns with CPA >3x target for 30+ days
- Use shared budgets for related campaigns to prevent overspend

---

## Implementation Checklist

**Weekly Tasks**:
- [ ] Review top 20 keywords by spend, adjust bids
- [ ] Add 5-10 new keywords from search terms report
- [ ] Add 10-15 negative keywords
- [ ] Check impression share trends

**Monthly Tasks**:
- [ ] Analyze Auction Insights for competitive changes
- [ ] Review campaign-level ROAS and reallocate budget
- [ ] Update bid formulas based on performance trends
- [ ] Audit match type distribution

**Quarterly Tasks**:
- [ ] Comprehensive keyword performance audit
- [ ] Competitor analysis deep dive
- [ ] Review and update target CPA/ROAS goals
- [ ] Landing page performance correlation analysis

---

## Success Metrics

**3-Month Goals**:
- Improve ROAS by 15-25%
- Reduce CPA by 10-20%
- Increase conversion rate by 5-10%
- Maintain or grow impression share for top keywords

**Continuous Optimization**:
- Weekly bid adjustments for top 50 keywords by spend
- Monthly addition of 20-30 new high-potential keywords
- Quarterly strategy review and refinement

---

## Notes for Future Implementation

**Data Requirements**:
- Minimum 3 months historical data for reliable trends
- Conversion tracking properly configured
- Google Ads API access or manual exports

**Automation Potential**:
- Bid adjustments can be automated via scripts
- Search term mining can be semi-automated with rules
- Competitive monitoring requires periodic manual review

**Common Pitfalls to Avoid**:
- Over-reacting to short-term fluctuations (use 7-day windows)
- Ignoring quality score (bid increases alone won't fix poor relevance)
- Not testing bid changes incrementally
- Forgetting to update negative keywords regularly
