{{
  config(
    materialized='view',
    tags=['staging', 'infrastructure']
  )
}}

/*
Staging model for infrastructure scoring from OpenStreetMap Overpass API.
Normalizes OSM data into structured format for analysis.

Source: s3://cloudclearing-data-lake/raw/infrastructure_scores/
Update frequency: Weekly (Monday 6am UTC via Step Functions)
*/

WITH source_data AS (
    SELECT
        json_extract_scalar(data, '$.region_name') AS region_name,
        json_extract_scalar(data, '$.analysis_date') AS analysis_date_raw,
        json_extract_scalar(data, '$.infrastructure_data.infrastructure_score') AS infrastructure_score_raw,
        json_extract_scalar(data, '$.infrastructure_data.highway_score') AS highway_score_raw,
        json_extract_scalar(data, '$.infrastructure_data.airport_score') AS airport_score_raw,
        json_extract_scalar(data, '$.infrastructure_data.railway_score') AS railway_score_raw,
        json_extract_scalar(data, '$.infrastructure_data.major_features') AS major_features_json,
        json_extract_scalar(data, '$.infrastructure_data.infrastructure_multiplier') AS infrastructure_multiplier_raw,
        json_extract_scalar(data, '$.infrastructure_data.accessibility_tier') AS accessibility_tier,
        json_extract_scalar(data, '$.infrastructure_data.cache_age_hours') AS cache_age_hours_raw,
        _file_modified_time AS source_file_timestamp
    FROM {{ source('raw', 'infrastructure_scores_json') }}
    WHERE json_extract_scalar(data, '$.region_name') IS NOT NULL
),

cleaned_data AS (
    SELECT
        -- Primary keys
        region_name,
        CAST(analysis_date_raw AS DATE) AS analysis_date,
        
        -- Infrastructure scores (normalized 0-100)
        CAST(infrastructure_score_raw AS DOUBLE) AS infrastructure_score,
        CAST(highway_score_raw AS DOUBLE) AS highway_score,
        CAST(airport_score_raw AS DOUBLE) AS airport_score,
        CAST(railway_score_raw AS DOUBLE) AS railway_score,
        
        -- Multiplier for investment scoring (0.8 to 1.3)
        CAST(infrastructure_multiplier_raw AS DOUBLE) AS infrastructure_multiplier,
        
        -- Categorical tier
        accessibility_tier,
        
        -- Data freshness
        CAST(cache_age_hours_raw AS DOUBLE) AS cache_age_hours,
        
        -- Major features (parse JSON array)
        major_features_json,
        
        -- Audit columns
        source_file_timestamp,
        CURRENT_TIMESTAMP AS loaded_at
        
    FROM source_data
    WHERE CAST(infrastructure_score_raw AS DOUBLE) BETWEEN 0 AND 100
)

SELECT
    *,
    -- Calculated fields
    CASE
        WHEN cache_age_hours < 24 THEN 'fresh'
        WHEN cache_age_hours < 168 THEN 'valid'  -- 1 week
        WHEN cache_age_hours < 336 THEN 'aging'  -- 2 weeks
        ELSE 'stale'
    END AS cache_freshness_category,
    
    CASE
        WHEN infrastructure_score >= 80 THEN 'excellent'
        WHEN infrastructure_score >= 60 THEN 'good'
        WHEN infrastructure_score >= 40 THEN 'moderate'
        WHEN infrastructure_score >= 20 THEN 'limited'
        ELSE 'poor'
    END AS infrastructure_tier,
    
    -- Feature counts (parse JSON array length)
    CARDINALITY(CAST(json_parse(major_features_json) AS ARRAY(VARCHAR))) AS major_features_count

FROM cleaned_data
