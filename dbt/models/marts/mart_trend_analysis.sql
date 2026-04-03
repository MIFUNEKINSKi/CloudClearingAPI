{{
  config(
    materialized='table',
    tags=['marts', 'analytics', 'trends']
  )
}}

/*
Mart: Trend Analysis
Aggregated time series insights across all regions.
Identifies market-wide patterns, seasonal trends, and leading indicators.

Target audience: Strategy team, market researchers
Update frequency: Weekly (after Step Functions run)
*/

WITH regional_trends AS (
    SELECT * FROM {{ ref('mart_region_performance') }}
),

weekly_aggregates AS (
    SELECT
        analysis_date,
        
        -- Aggregate investment scores
        AVG(final_investment_score) AS avg_investment_score,
        MIN(final_investment_score) AS min_investment_score,
        MAX(final_investment_score) AS max_investment_score,
        STDDEV(final_investment_score) AS stdev_investment_score,
        
        -- Count by recommendation
        SUM(CASE WHEN investment_recommendation = 'BUY' THEN 1 ELSE 0 END) AS buy_count,
        SUM(CASE WHEN investment_recommendation = 'WATCH' THEN 1 ELSE 0 END) AS watch_count,
        SUM(CASE WHEN investment_recommendation = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
        COUNT(*) AS total_regions,
        
        -- Financial aggregates
        AVG(projected_roi_3yr_pct) AS avg_roi_3yr,
        MEDIAN(projected_roi_3yr_pct) AS median_roi_3yr,
        AVG(price_per_m2_usd) AS avg_price_per_m2_usd,
        MEDIAN(price_per_m2_usd) AS median_price_per_m2_usd,
        SUM(estimated_investment_usd) AS total_investment_opportunity_usd,
        SUM(total_estimated_profit_usd) AS total_profit_potential_usd,
        
        -- Development activity
        AVG(satellite_total_changes) AS avg_satellite_changes,
        SUM(satellite_total_changes) AS total_satellite_changes,
        AVG(construction_activity_pct) AS avg_construction_activity,
        SUM(area_affected_m2) AS total_area_affected_m2,
        
        -- Infrastructure
        AVG(infrastructure_score) AS avg_infrastructure_score,
        SUM(CASE WHEN infrastructure_tier = 'excellent' THEN 1 ELSE 0 END) AS excellent_infrastructure_count,
        
        -- Market heat
        SUM(CASE WHEN market_heat = 'hot' THEN 1 ELSE 0 END) AS hot_markets_count,
        SUM(CASE WHEN market_heat = 'warming' THEN 1 ELSE 0 END) AS warming_markets_count,
        SUM(CASE WHEN market_momentum LIKE '%uptrend%' THEN 1 ELSE 0 END) AS positive_momentum_count,
        
        -- Data quality
        AVG(data_completeness_score) AS avg_data_completeness,
        SUM(CASE WHEN overall_data_quality = 'high_quality' THEN 1 ELSE 0 END) AS high_quality_data_count
        
    FROM regional_trends
    WHERE is_current_week = TRUE
    GROUP BY analysis_date
),

time_series_trends AS (
    SELECT
        *,
        -- Week-over-week market changes
        LAG(avg_investment_score, 1) OVER (ORDER BY analysis_date) AS prev_week_avg_score,
        LAG(avg_roi_3yr, 1) OVER (ORDER BY analysis_date) AS prev_week_avg_roi,
        LAG(avg_price_per_m2_usd, 1) OVER (ORDER BY analysis_date) AS prev_week_avg_price,
        
        -- 4-week rolling averages
        AVG(avg_investment_score) OVER (
            ORDER BY analysis_date 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS score_4wk_ma,
        
        AVG(buy_count) OVER (
            ORDER BY analysis_date 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS buy_count_4wk_ma,
        
        -- Market sentiment score (0-100)
        (CAST(buy_count AS DOUBLE) / CAST(total_regions AS DOUBLE)) * 100.0 AS market_buy_sentiment_pct,
        (CAST(hot_markets_count + warming_markets_count AS DOUBLE) / CAST(total_regions AS DOUBLE)) * 100.0 AS market_heat_pct
        
    FROM weekly_aggregates
)

SELECT
    analysis_date,
    
    -- Investment scores
    avg_investment_score,
    min_investment_score,
    max_investment_score,
    stdev_investment_score,
    score_4wk_ma,
    
    -- Recommendation distribution
    buy_count,
    watch_count,
    pass_count,
    total_regions,
    market_buy_sentiment_pct,
    buy_count_4wk_ma,
    
    -- Financial metrics
    avg_roi_3yr,
    median_roi_3yr,
    avg_price_per_m2_usd,
    median_price_per_m2_usd,
    total_investment_opportunity_usd,
    total_profit_potential_usd,
    
    -- Development activity
    avg_satellite_changes,
    total_satellite_changes,
    avg_construction_activity,
    total_area_affected_m2,
    
    -- Infrastructure
    avg_infrastructure_score,
    excellent_infrastructure_count,
    
    -- Market conditions
    hot_markets_count,
    warming_markets_count,
    positive_momentum_count,
    market_heat_pct,
    
    -- Data quality
    avg_data_completeness,
    high_quality_data_count,
    
    -- Week-over-week changes
    CASE 
        WHEN prev_week_avg_score IS NOT NULL AND prev_week_avg_score > 0
        THEN ((avg_investment_score - prev_week_avg_score) / prev_week_avg_score) * 100.0
        ELSE NULL
    END AS avg_score_wow_change_pct,
    
    CASE 
        WHEN prev_week_avg_roi IS NOT NULL AND prev_week_avg_roi > 0
        THEN ((avg_roi_3yr - prev_week_avg_roi) / prev_week_avg_roi) * 100.0
        ELSE NULL
    END AS avg_roi_wow_change_pct,
    
    CASE 
        WHEN prev_week_avg_price IS NOT NULL AND prev_week_avg_price > 0
        THEN ((avg_price_per_m2_usd - prev_week_avg_price) / prev_week_avg_price) * 100.0
        ELSE NULL
    END AS avg_price_wow_change_pct,
    
    -- Market trend classification
    CASE
        WHEN market_buy_sentiment_pct >= 40 AND avg_score_wow_change_pct > 5 THEN 'bull_market'
        WHEN market_buy_sentiment_pct >= 30 THEN 'bullish'
        WHEN market_buy_sentiment_pct >= 20 THEN 'neutral'
        WHEN avg_score_wow_change_pct < -5 THEN 'bearish'
        ELSE 'bear_market'
    END AS overall_market_trend,
    
    -- Opportunity index (composite metric)
    (market_buy_sentiment_pct * 0.4) + 
    (market_heat_pct * 0.3) + 
    (avg_investment_score * 0.3) AS market_opportunity_index

FROM time_series_trends
ORDER BY analysis_date DESC
