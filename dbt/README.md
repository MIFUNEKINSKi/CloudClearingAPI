# CloudClearing Analytics - dbt Project

## Overview

This dbt (data build tool) project transforms raw satellite, infrastructure, and market data from the CloudClearingAPI pipeline into analytics-ready datasets for investment decision-making.

**Version**: 1.0.0  
**Target Database**: AWS Athena / Trino  
**Update Frequency**: Weekly (Monday 6am UTC via Step Functions)

---

## Architecture

### Data Flow
```
S3 Raw Data (JSON) 
    ↓
Staging Models (Views) 
    ↓ 
Intermediate Models (Views)
    ↓
Mart Models (Tables/Incremental)
    ↓
BI Tools / Dashboards
```

### Model Layers

#### 1. **Staging** (`models/staging/`)
- **Purpose**: Raw data ingestion with minimal transformation
- **Materialization**: Views
- **Update Strategy**: Full refresh
- **Models**:
  - `stg_satellite_changes`: Sentinel-2 change detection data
  - `stg_infrastructure_scores`: OSM infrastructure metrics
  - `stg_market_data`: Market intelligence (scraped + benchmarks)
  - `stg_financial_projections`: ROI and financial forecasts

#### 2. **Intermediate** (`models/intermediate/`)
- **Purpose**: Business logic transformations and enrichment
- **Materialization**: Views
- **Update Strategy**: Full refresh
- **Models**:
  - `int_region_metrics_enriched`: Joins all staging layers
  - `int_investment_scores_calculated`: Investment scoring logic
  - `int_time_series_aggregated`: Rolling averages and trends

#### 3. **Marts** (`models/marts/`)
- **Purpose**: Final consumption layer for analytics
- **Materialization**: Tables (some incremental)
- **Update Strategy**: Incremental on `analysis_date`
- **Models**:
  - `mart_investment_dashboard`: Executive summary (current week)
  - `mart_region_performance`: Detailed historical analytics
  - `mart_trend_analysis`: Market-wide trend insights
  - `mart_roi_projections`: Financial forecasting and scenarios

---

## Setup

### Prerequisites
- dbt Core 1.5+ or dbt Cloud account
- AWS credentials with Athena access
- Python 3.8+

### Installation

```bash
# 1. Install dbt with Athena adapter
pip install dbt-core dbt-athena-community

# 2. Install dbt packages
cd dbt/
dbt deps

# 3. Configure profiles (see profiles.yml)
# Copy to ~/.dbt/profiles.yml and update credentials
```

### Configuration

Edit `~/.dbt/profiles.yml`:
```yaml
cloudclearing:
  target: prod
  outputs:
    prod:
      type: athena
      s3_staging_dir: s3://cloudclearing-data-lake/athena-results/
      region_name: ap-southeast-1
      database: cloudclearing
      schema: analytics_prod
      work_group: primary
      aws_profile_name: cloudclearing-prod
```

---

## Usage

### Running Models

```bash
# Run all models
dbt run

# Run specific layers
dbt run --select staging
dbt run --select intermediate
dbt run --select marts

# Run specific model
dbt run --select mart_investment_dashboard

# Run with full refresh (ignore incremental)
dbt run --full-refresh
```

### Testing

```bash
# Run all tests
dbt test

# Test specific model
dbt test --select stg_satellite_changes

# Test data sources freshness
dbt source freshness
```

### Documentation

```bash
# Generate documentation
dbt docs generate

# Serve documentation site
dbt docs serve
```

---

## Model Dependencies

```
sources (S3 JSON files)
    ↓
stg_satellite_changes ──┐
stg_infrastructure_scores ─┼─→ int_region_metrics_enriched
stg_market_data ──────────┤       ↓
stg_financial_projections ─┘   int_investment_scores_calculated
                                   ↓
                               int_time_series_aggregated
                                   ↓
        ┌──────────────────────────┼──────────────────────────┐
        ↓                          ↓                          ↓
mart_investment_dashboard  mart_region_performance  mart_trend_analysis
                                   ↓
                           mart_roi_projections
```

---

## Data Quality Tests

### Staging Layer (34 tests)
- **Not null**: All primary keys and critical metrics
- **Accepted values**: Categorical fields (data_freshness_category, risk_category, etc.)
- **Range checks**: Numeric bounds (scores 0-100, multipliers 0.8-1.3, ROI -50% to 300%)
- **Relationships**: Foreign key integrity between staging tables

### Custom Tests
- **Freshness**: Data must be < 14 days old
- **Completeness**: No missing satellite data for analyzed regions
- **Consistency**: Infrastructure scores match multiplier calculations

---

## Incremental Strategy

Mart models use incremental materialization for performance:

```sql
{{
  config(
    materialized='incremental',
    unique_key='region_name',
    on_schema_change='sync_all_columns'
  )
}}

...

{% if is_incremental() %}
WHERE analysis_date > (SELECT MAX(analysis_date) FROM {{ this }})
{% endif %}
```

**Benefits**:
- Faster runs (only process new data)
- Lower compute costs
- Maintains historical data

---

## Macros

### `calculate_score_multiplier`
Converts scores (0-100) to multipliers (0.8-1.3) for investment scoring.

```sql
SELECT
    region_name,
    {{ calculate_score_multiplier('infrastructure_score') }} AS infra_multiplier
FROM staging_data
```

### `investment_recommendation`
Generates BUY/WATCH/PASS based on score thresholds.

```sql
SELECT
    region_name,
    {{ investment_recommendation('final_investment_score') }} AS recommendation
FROM scored_data
```

### `audit_columns`
Adds standard audit metadata to models.

```sql
SELECT
    *,
    {{ audit_columns() }}
FROM source_data
```

---

## Integration with Step Functions

The dbt project integrates into the CloudClearingAPI Step Functions workflow:

```json
{
  "dbt_transform": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "cloudclearing-dbt-runner",
      "Payload": {
        "command": "dbt run --select marts",
        "target": "prod"
      }
    }
  }
}
```

**Execution Order**:
1. Satellite analysis (GEE queries)
2. Infrastructure analysis (OSM queries)
3. Market intelligence (web scraping)
4. Financial projections
5. **→ dbt transformations** ← (this project)
6. PDF report generation

---

## Performance Optimization

### Query Optimization
- **Partition pruning**: All queries filter on `analysis_date`
- **Columnar storage**: Use Parquet format for S3 data
- **Incremental models**: Only process new data after initial run

### Cost Optimization
- **Views for intermediate**: No storage costs
- **Tables for marts**: Query performance over storage cost
- **Incremental updates**: Minimize data scanned per run

### Monitoring
```bash
# Check model run times
dbt run --select marts --log-level debug

# Profile query performance
dbt run --profiles-dir . --profile cloudclearing --target prod --log-level debug
```

---

## Troubleshooting

### Issue: "Image.select: Band pattern 'B4' was applied to an Image with no bands"
**Cause**: Empty satellite composites from fallback logic  
**Solution**: Check `fallback_weeks_used` in staging data, verify GEE cache

### Issue: "Athena query timeout"
**Cause**: Large data scans without partition pruning  
**Solution**: Add `WHERE analysis_date >= '2025-01-01'` filters

### Issue: "dbt test failures on accepted_values"
**Cause**: New categorical values not in test config  
**Solution**: Update `schema.yml` accepted_values lists

### Issue: "Incremental model not updating"
**Cause**: No new data or unique_key conflict  
**Solution**: Run with `--full-refresh` once, check source data freshness

---

## Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/new-mart-model
   ```

2. **Develop model**
   ```bash
   # Create SQL file in models/marts/
   dbt run --select my_new_model
   dbt test --select my_new_model
   ```

3. **Add tests**
   ```yaml
   # Add to schema.yml
   models:
     - name: my_new_model
       tests: [...]
   ```

4. **Document**
   ```bash
   dbt docs generate
   dbt docs serve
   ```

5. **Deploy**
   ```bash
   dbt run --target prod
   ```

---

## Resources

- **dbt Docs**: https://docs.getdbt.com/
- **Athena Adapter**: https://github.com/dbt-athena/dbt-athena-adapter
- **CloudClearingAPI**: https://github.com/MIFUNEKINSKi/CloudClearingAPI
- **Step Functions Guide**: `docs/deployment/step-functions-guide.md`

---

## License

Proprietary - CloudClearingAPI © 2025
