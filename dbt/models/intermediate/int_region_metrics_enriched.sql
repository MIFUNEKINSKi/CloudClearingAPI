{{
  config(
    materialized='view',
    tags=['intermediate', 'enrichment']
  )
}}

/*
Intermediate model: Region Metrics Enriched
Joins all staging layers to create complete regional dataset.
One row per region per analysis date with all metrics combined.

Dependencies: stg_satellite_changes, stg_infrastructure_scores, 
              stg_market_data, stg_financial_projections
*/

WITH satellite AS (
    SELECT * FROM {{ ref('stg_satellite_changes') }}
),

infrastructure AS (
    SELECT * FROM {{ ref('stg_infrastructure_scores') }}
),

market AS (
    SELECT * FROM {{ ref('stg_market_data') }}
),

financial AS (
    SELECT * FROM {{ ref('stg_financial_projections') }}
),

joined_data AS (
    SELECT
        -- Primary keys
        s.region_name,
        s.analysis_date,
        
        -- Satellite metrics
        s.vegetation_loss_pixels,
        s.construction_activity_pct,
        s.bare_soil_expansion_m2,
        s.total_changes AS satellite_total_changes,
        s.area_affected_m2,
        s.cloud_coverage_pct,
        s.imagery_date,
        s.data_freshness_category AS satellite_data_freshness,
        s.imagery_quality_tier,
        s.fallback_weeks_used,
        
        -- Infrastructure metrics
        i.infrastructure_score,
        i.highway_score,
        i.airport_score,
        i.railway_score,
        i.infrastructure_multiplier,
        i.accessibility_tier,
        i.infrastructure_tier,
        i.major_features_count,
        i.cache_freshness_category AS infrastructure_cache_freshness,
        
        -- Market metrics
        m.price_per_m2_idr,
        m.price_per_m2_usd,
        m.price_trend_30d_pct,
        m.market_heat,
        m.active_listings_count,
        m.market_multiplier,
        m.market_momentum,
        m.data_source AS market_data_source,
        m.confidence_level AS market_confidence_level,
        m.data_reliability_tier AS market_reliability_tier,
        
        -- Financial projections
        f.current_land_value_per_m2_idr,
        f.current_land_value_per_m2_usd,
        f.projected_value_3yr_per_m2_idr,
        f.projected_value_3yr_per_m2_usd,
        f.projected_roi_3yr_pct,
        f.payback_period_years,
        f.recommended_plot_size_m2,
        f.estimated_investment_idr,
        f.estimated_investment_usd,
        f.total_estimated_profit_idr,
        f.total_estimated_profit_usd,
        f.risk_category,
        f.roi_tier,
        f.payback_speed,
        f.confidence_score AS financial_confidence_score,
        f.land_appreciation_3yr_pct,
        
        -- Geospatial data
        s.latitude,
        s.longitude,
        s.bbox_west,
        s.bbox_south,
        s.bbox_east,
        s.bbox_north,
        
        -- Audit columns
        s.loaded_at AS satellite_loaded_at,
        i.loaded_at AS infrastructure_loaded_at,
        m.loaded_at AS market_loaded_at,
        f.loaded_at AS financial_loaded_at,
        CURRENT_TIMESTAMP AS enriched_at
        
    FROM satellite s
    INNER JOIN infrastructure i
        ON s.region_name = i.region_name
        AND s.analysis_date = i.analysis_date
    INNER JOIN market m
        ON s.region_name = m.region_name
        AND s.analysis_date = m.analysis_date
    LEFT JOIN financial f
        ON s.region_name = f.region_name
        AND s.analysis_date = f.analysis_date
)

SELECT
    *,
    -- Data completeness score (0-100)
    CASE
        WHEN satellite_total_changes IS NOT NULL 
         AND infrastructure_score IS NOT NULL 
         AND price_per_m2_idr IS NOT NULL 
         AND projected_roi_3yr_pct IS NOT NULL
        THEN 100.0
        WHEN satellite_total_changes IS NOT NULL 
         AND infrastructure_score IS NOT NULL 
         AND price_per_m2_idr IS NOT NULL
        THEN 75.0
        WHEN satellite_total_changes IS NOT NULL 
         AND infrastructure_score IS NOT NULL
        THEN 50.0
        ELSE 25.0
    END AS data_completeness_score,
    
    -- Overall data quality flag
    CASE
        WHEN imagery_quality_tier IN ('excellent', 'good')
         AND infrastructure_cache_freshness IN ('fresh', 'valid')
         AND market_reliability_tier = 'high'
        THEN 'high_quality'
        WHEN imagery_quality_tier IN ('good', 'acceptable')
         AND infrastructure_cache_freshness IN ('valid', 'aging')
         AND market_reliability_tier IN ('high', 'medium')
        THEN 'medium_quality'
        ELSE 'low_quality'
    END AS overall_data_quality

FROM joined_data
