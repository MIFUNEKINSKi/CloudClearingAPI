{{
  config(
    materialized='incremental',
    unique_key='region_name',
    on_schema_change='sync_all_columns',
    tags=['marts', 'dashboard']
  )
}}

/*
Mart: Investment Dashboard
Executive summary view for current week's investment opportunities.
One row per region with latest metrics and recommendations.

Target audience: Executives, investors, decision-makers
Update frequency: Weekly (after Step Functions run)
*/

WITH latest_analysis AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY region_name ORDER BY analysis_date DESC) AS rn
    FROM {{ ref('int_time_series_aggregated') }}
    {% if is_incremental() %}
    WHERE analysis_date > (SELECT MAX(analysis_date) FROM {{ this }})
    {% endif %}
),

current_week AS (
    SELECT * 
    FROM latest_analysis 
    WHERE rn = 1
)

SELECT
    -- Region identification
    region_name,
    analysis_date,
    latitude,
    longitude,
    
    -- Investment score & recommendation
    final_investment_score,
    investment_recommendation,
    priority_tier,
    composite_confidence_score,
    
    -- Score components
    satellite_component,
    infrastructure_boost,
    market_boost,
    satellite_contribution_pct,
    infrastructure_contribution_pct,
    market_contribution_pct,
    
    -- Financial metrics
    projected_roi_3yr_pct,
    roi_tier,
    payback_period_years,
    estimated_investment_usd,
    total_estimated_profit_usd,
    recommended_plot_size_m2,
    risk_category,
    
    -- Market conditions
    price_per_m2_usd,
    market_heat,
    market_momentum,
    price_trend_30d_pct,
    
    -- Development indicators
    satellite_total_changes,
    construction_activity_pct,
    area_affected_m2,
    
    -- Infrastructure
    infrastructure_score,
    infrastructure_tier,
    accessibility_tier,
    major_features_count,
    
    -- Trends
    investment_trend,
    momentum_category,
    investment_score_wow_change_pct,
    price_wow_change_pct,
    
    -- Data quality
    overall_data_quality,
    data_completeness_score,
    imagery_quality_tier,
    market_reliability_tier,
    
    -- Audit
    enriched_at AS last_updated,
    
    -- Derived flags for quick filtering
    CASE WHEN investment_recommendation = 'BUY' THEN TRUE ELSE FALSE END AS is_buy_recommendation,
    CASE WHEN projected_roi_3yr_pct >= 0.30 THEN TRUE ELSE FALSE END AS is_high_roi,
    CASE WHEN final_investment_score >= 70 AND risk_category IN ('low', 'medium') THEN TRUE ELSE FALSE END AS is_low_risk_opportunity,
    CASE WHEN momentum_category LIKE '%upward%' THEN TRUE ELSE FALSE END AS is_positive_momentum,
    
    -- Summary metrics for quick insights
    CONCAT(
        'Score: ', CAST(ROUND(final_investment_score, 1) AS VARCHAR),
        ' | ROI: ', CAST(ROUND(projected_roi_3yr_pct * 100, 1) AS VARCHAR), '%',
        ' | Risk: ', risk_category,
        ' | Trend: ', investment_trend
    ) AS quick_summary

FROM current_week
