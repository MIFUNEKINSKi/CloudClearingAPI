{{
  config(
    materialized='view',
    tags=['staging', 'market']
  )
}}

/*
Staging model for market intelligence data from web scraping (Lamudi, Rumah.com).
Handles 3-tier fallback: Live scraping > Cache > Static benchmarks.

Source: s3://cloudclearing-data-lake/raw/market_data/
Update frequency: Weekly (Monday 6am UTC via Step Functions)
*/

WITH source_data AS (
    SELECT
        json_extract_scalar(data, '$.region_name') AS region_name,
        json_extract_scalar(data, '$.analysis_date') AS analysis_date_raw,
        json_extract_scalar(data, '$.market_data.price_per_m2_idr') AS price_per_m2_idr_raw,
        json_extract_scalar(data, '$.market_data.price_trend_30d') AS price_trend_30d_raw,
        json_extract_scalar(data, '$.market_data.market_heat') AS market_heat,
        json_extract_scalar(data, '$.market_data.active_listings') AS active_listings_raw,
        json_extract_scalar(data, '$.market_data.market_multiplier') AS market_multiplier_raw,
        json_extract_scalar(data, '$.market_data.data_source') AS data_source,
        json_extract_scalar(data, '$.market_data.confidence_level') AS confidence_level_raw,
        json_extract_scalar(data, '$.market_data.data_age_hours') AS data_age_hours_raw,
        json_extract_scalar(data, '$.market_data.scrape_success') AS scrape_success_raw,
        _file_modified_time AS source_file_timestamp
    FROM {{ source('raw', 'market_data_json') }}
    WHERE json_extract_scalar(data, '$.region_name') IS NOT NULL
),

cleaned_data AS (
    SELECT
        -- Primary keys
        region_name,
        CAST(analysis_date_raw AS DATE) AS analysis_date,
        
        -- Market pricing (Indonesian Rupiah per square meter)
        CAST(price_per_m2_idr_raw AS BIGINT) AS price_per_m2_idr,
        CAST(price_trend_30d_raw AS DOUBLE) AS price_trend_30d_pct,
        
        -- Market activity indicators
        CAST(active_listings_raw AS INT) AS active_listings_count,
        market_heat,  -- 'hot', 'warming', 'stable', 'cooling'
        
        -- Investment multiplier (0.85 to 1.4)
        CAST(market_multiplier_raw AS DOUBLE) AS market_multiplier,
        
        -- Data provenance tracking
        data_source,  -- 'live_scrape', 'cache', 'static_benchmark'
        CAST(confidence_level_raw AS DOUBLE) AS confidence_level,
        CAST(data_age_hours_raw AS DOUBLE) AS data_age_hours,
        CAST(scrape_success_raw AS BOOLEAN) AS scrape_success,
        
        -- Audit columns
        source_file_timestamp,
        CURRENT_TIMESTAMP AS loaded_at
        
    FROM source_data
    WHERE CAST(price_per_m2_idr_raw AS BIGINT) > 0  -- Filter invalid prices
)

SELECT
    *,
    -- Calculated fields
    CASE
        WHEN data_source = 'live_scrape' THEN 'high'
        WHEN data_source = 'cache' THEN 'medium'
        WHEN data_source = 'static_benchmark' THEN 'low'
        ELSE 'unknown'
    END AS data_reliability_tier,
    
    CASE
        WHEN data_age_hours < 24 THEN 'fresh'
        WHEN data_age_hours < 168 THEN 'valid'  -- 1 week
        WHEN data_age_hours < 720 THEN 'aging'  -- 30 days
        ELSE 'stale'
    END AS data_freshness_category,
    
    CASE
        WHEN market_heat = 'hot' AND price_trend_30d_pct > 0.05 THEN 'strong_uptrend'
        WHEN market_heat = 'warming' AND price_trend_30d_pct > 0 THEN 'moderate_uptrend'
        WHEN price_trend_30d_pct BETWEEN -0.02 AND 0.02 THEN 'stable'
        WHEN price_trend_30d_pct < 0 THEN 'downtrend'
        ELSE 'uncertain'
    END AS market_momentum,
    
    -- Currency conversion helpers (assuming 1 USD = 15,700 IDR as of 2025)
    CAST(price_per_m2_idr AS DOUBLE) / 15700.0 AS price_per_m2_usd

FROM cleaned_data
