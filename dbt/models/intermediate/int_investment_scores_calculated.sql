{{
  config(
    materialized='view',
    tags=['intermediate', 'scoring']
  )
}}

/*
Intermediate model: Investment Scores Calculated
Replicates CloudClearingAPI's corrected scoring logic in SQL.
Base score (0-40) from satellite + infrastructure multiplier + market multiplier.

Dependencies: int_region_metrics_enriched
*/

WITH enriched_data AS (
    SELECT * FROM {{ ref('int_region_metrics_enriched') }}
),

base_scores AS (
    SELECT
        region_name,
        analysis_date,
        satellite_total_changes,
        area_affected_m2,
        
        -- Base activity score from satellite data (0-40 points)
        -- Mirrors logic in src/core/corrected_scoring.py
        LEAST(40.0, 
            (CAST(satellite_total_changes AS DOUBLE) / 1000.0 * 10.0) +
            (CAST(area_affected_m2 AS DOUBLE) / 10000.0 * 5.0) +
            (construction_activity_pct * 100.0)
        ) AS base_activity_score,
        
        -- Multipliers
        COALESCE(infrastructure_multiplier, 1.0) AS infra_mult,
        COALESCE(market_multiplier, 1.0) AS market_mult,
        
        -- Keep all original fields
        *
        
    FROM enriched_data
),

calculated_scores AS (
    SELECT
        *,
        -- Final investment score (0-100)
        LEAST(100.0,
            base_activity_score * infra_mult * market_mult
        ) AS final_investment_score,
        
        -- Component contributions
        base_activity_score AS satellite_component,
        (base_activity_score * infra_mult) - base_activity_score AS infrastructure_boost,
        (base_activity_score * infra_mult * market_mult) - (base_activity_score * infra_mult) AS market_boost
        
    FROM base_scores
)

SELECT
    *,
    -- Investment recommendation
    CASE
        WHEN final_investment_score >= 70 THEN 'BUY'
        WHEN final_investment_score >= 50 THEN 'WATCH'
        ELSE 'PASS'
    END AS investment_recommendation,
    
    -- Priority tier
    CASE
        WHEN final_investment_score >= 70 THEN 'high'
        WHEN final_investment_score >= 50 THEN 'medium'
        WHEN final_investment_score >= 30 THEN 'low'
        ELSE 'none'
    END AS priority_tier,
    
    -- Score breakdown percentages
    CASE WHEN final_investment_score > 0 
        THEN (satellite_component / final_investment_score) * 100.0 
        ELSE 0.0 
    END AS satellite_contribution_pct,
    
    CASE WHEN final_investment_score > 0 
        THEN (infrastructure_boost / final_investment_score) * 100.0 
        ELSE 0.0 
    END AS infrastructure_contribution_pct,
    
    CASE WHEN final_investment_score > 0 
        THEN (market_boost / final_investment_score) * 100.0 
        ELSE 0.0 
    END AS market_contribution_pct,
    
    -- Confidence weighting (combines data quality and financial confidence)
    (data_completeness_score / 100.0) * 
    COALESCE(financial_confidence_score, 0.5) * 
    CASE 
        WHEN overall_data_quality = 'high_quality' THEN 1.0
        WHEN overall_data_quality = 'medium_quality' THEN 0.8
        ELSE 0.6
    END AS composite_confidence_score

FROM calculated_scores
