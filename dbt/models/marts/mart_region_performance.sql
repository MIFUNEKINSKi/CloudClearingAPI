{{
  config(
    materialized='incremental',
    unique_key=['region_name', 'analysis_date'],
    on_schema_change='sync_all_columns',
    tags=['marts', 'analytics']
  )
}}

/*
Mart: Region Performance
Detailed historical performance analytics for each region.
Tracks all metrics over time for trend analysis and forecasting.

Target audience: Analysts, data scientists, researchers
Update frequency: Weekly (after Step Functions run)
*/

WITH time_series AS (
    SELECT *
    FROM {{ ref('int_time_series_aggregated') }}
    {% if is_incremental() %}
    WHERE analysis_date > (SELECT MAX(analysis_date) FROM {{ this }})
    {% endif %}
)

SELECT
    -- Primary keys
    region_name,
    analysis_date,
    weeks_ago,
    is_current_week,
    
    -- Investment metrics
    final_investment_score,
    investment_recommendation,
    priority_tier,
    composite_confidence_score,
    base_activity_score,
    infra_mult AS infrastructure_multiplier,
    market_mult AS market_multiplier,
    
    -- Satellite activity
    satellite_total_changes,
    vegetation_loss_pixels,
    construction_activity_pct,
    bare_soil_expansion_m2,
    area_affected_m2,
    cloud_coverage_pct,
    imagery_quality_tier,
    fallback_weeks_used,
    
    -- Infrastructure
    infrastructure_score,
    highway_score,
    airport_score,
    railway_score,
    infrastructure_tier,
    accessibility_tier,
    major_features_count,
    
    -- Market data
    price_per_m2_idr,
    price_per_m2_usd,
    price_trend_30d_pct,
    market_heat,
    market_momentum,
    active_listings_count,
    market_data_source,
    market_confidence_level,
    market_reliability_tier,
    
    -- Financial projections
    current_land_value_per_m2_usd,
    projected_value_3yr_per_m2_usd,
    projected_roi_3yr_pct,
    payback_period_years,
    recommended_plot_size_m2,
    estimated_investment_usd,
    total_estimated_profit_usd,
    risk_category,
    roi_tier,
    payback_speed,
    financial_confidence_score,
    land_appreciation_3yr_pct,
    
    -- Rolling averages
    investment_score_4wk_avg,
    investment_score_8wk_avg,
    roi_4wk_avg,
    price_4wk_avg,
    
    -- Week-over-week changes
    investment_score_wow_change_pct,
    price_wow_change_pct,
    satellite_activity_wow_change_pct,
    
    -- Trends & momentum
    investment_trend,
    momentum_category,
    score_volatility,
    
    -- Data quality
    overall_data_quality,
    data_completeness_score,
    
    -- Geospatial
    latitude,
    longitude,
    bbox_west,
    bbox_south,
    bbox_east,
    bbox_north,
    
    -- Audit
    satellite_loaded_at,
    infrastructure_loaded_at,
    market_loaded_at,
    financial_loaded_at,
    enriched_at,
    
    -- Computed metrics for analysis
    CASE 
        WHEN investment_score_prev_week IS NOT NULL 
        THEN final_investment_score - investment_score_prev_week 
        ELSE NULL 
    END AS investment_score_absolute_change,
    
    CASE
        WHEN price_prev_week IS NOT NULL
        THEN price_per_m2_idr - price_prev_week
        ELSE NULL
    END AS price_absolute_change_idr,
    
    -- Performance classification
    CASE
        WHEN final_investment_score >= 70 AND investment_score_wow_change_pct > 0 THEN 'star_performer'
        WHEN final_investment_score >= 70 THEN 'stable_leader'
        WHEN final_investment_score >= 50 AND investment_score_wow_change_pct > 10 THEN 'rising_star'
        WHEN final_investment_score >= 50 THEN 'steady_performer'
        WHEN investment_score_wow_change_pct < -10 THEN 'declining'
        ELSE 'underperformer'
    END AS performance_classification

FROM time_series
