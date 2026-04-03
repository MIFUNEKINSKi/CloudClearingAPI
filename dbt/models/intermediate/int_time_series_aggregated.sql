{{
  config(
    materialized='view',
    tags=['intermediate', 'time_series']
  )
}}

/*
Intermediate model: Time Series Aggregated
Calculates rolling averages, trends, and momentum indicators.
Enables week-over-week and month-over-month comparisons.

Dependencies: int_investment_scores_calculated
*/

WITH scored_data AS (
    SELECT * FROM {{ ref('int_investment_scores_calculated') }}
),

windowed_metrics AS (
    SELECT
        region_name,
        analysis_date,
        final_investment_score,
        projected_roi_3yr_pct,
        price_per_m2_idr,
        satellite_total_changes,
        
        -- 4-week rolling averages
        AVG(final_investment_score) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS investment_score_4wk_avg,
        
        AVG(projected_roi_3yr_pct) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS roi_4wk_avg,
        
        AVG(price_per_m2_idr) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS price_4wk_avg,
        
        -- Previous week values (lag)
        LAG(final_investment_score, 1) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date
        ) AS investment_score_prev_week,
        
        LAG(price_per_m2_idr, 1) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date
        ) AS price_prev_week,
        
        LAG(satellite_total_changes, 1) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date
        ) AS satellite_changes_prev_week,
        
        -- 8-week rolling averages for longer trends
        AVG(final_investment_score) OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date 
            ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
        ) AS investment_score_8wk_avg,
        
        -- Rank within region history
        ROW_NUMBER() OVER (
            PARTITION BY region_name 
            ORDER BY analysis_date DESC
        ) AS weeks_ago,
        
        -- Keep all original columns
        *
        
    FROM scored_data
)

SELECT
    *,
    -- Week-over-week changes
    CASE 
        WHEN investment_score_prev_week IS NOT NULL AND investment_score_prev_week > 0
        THEN ((final_investment_score - investment_score_prev_week) / investment_score_prev_week) * 100.0
        ELSE NULL
    END AS investment_score_wow_change_pct,
    
    CASE 
        WHEN price_prev_week IS NOT NULL AND price_prev_week > 0
        THEN ((CAST(price_per_m2_idr AS DOUBLE) - CAST(price_prev_week AS DOUBLE)) / CAST(price_prev_week AS DOUBLE)) * 100.0
        ELSE NULL
    END AS price_wow_change_pct,
    
    CASE 
        WHEN satellite_changes_prev_week IS NOT NULL AND satellite_changes_prev_week > 0
        THEN ((CAST(satellite_total_changes AS DOUBLE) - CAST(satellite_changes_prev_week AS DOUBLE)) / CAST(satellite_changes_prev_week AS DOUBLE)) * 100.0
        ELSE NULL
    END AS satellite_activity_wow_change_pct,
    
    -- Trend indicators
    CASE
        WHEN investment_score_4wk_avg > investment_score_8wk_avg THEN 'accelerating'
        WHEN investment_score_4wk_avg < investment_score_8wk_avg THEN 'decelerating'
        ELSE 'stable'
    END AS investment_trend,
    
    -- Momentum classification
    CASE
        WHEN final_investment_score > investment_score_4wk_avg + 10 THEN 'strong_upward'
        WHEN final_investment_score > investment_score_4wk_avg + 5 THEN 'moderate_upward'
        WHEN final_investment_score < investment_score_4wk_avg - 10 THEN 'strong_downward'
        WHEN final_investment_score < investment_score_4wk_avg - 5 THEN 'moderate_downward'
        ELSE 'stable'
    END AS momentum_category,
    
    -- Data recency flag
    CASE
        WHEN weeks_ago = 1 THEN TRUE
        ELSE FALSE
    END AS is_current_week,
    
    -- Volatility measure (standard deviation proxy)
    ABS(final_investment_score - investment_score_4wk_avg) AS score_volatility

FROM windowed_metrics
