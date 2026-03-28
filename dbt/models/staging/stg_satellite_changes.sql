{{
  config(
    materialized='view',
    tags=['staging', 'satellite']
  )
}}

/*
Staging model for satellite change detection data from Google Earth Engine.
Reads from S3 raw JSON outputs and normalizes into structured table.

Source: s3://cloudclearing-data-lake/raw/satellite_changes/
Update frequency: Weekly (Monday 6am UTC via Step Functions)
*/

WITH source_data AS (
    SELECT
        -- Use dbt_utils to read from external JSON files in S3
        json_extract_scalar(data, '$.region_name') AS region_name,
        json_extract_scalar(data, '$.analysis_date') AS analysis_date_raw,
        json_extract_scalar(data, '$.satellite_data.vegetation_loss_pixels') AS vegetation_loss_pixels_raw,
        json_extract_scalar(data, '$.satellite_data.construction_activity_pct') AS construction_activity_pct_raw,
        json_extract_scalar(data, '$.satellite_data.bare_soil_expansion_m2') AS bare_soil_expansion_m2_raw,
        json_extract_scalar(data, '$.satellite_data.total_changes') AS total_changes_raw,
        json_extract_scalar(data, '$.satellite_data.area_affected_m2') AS area_affected_m2_raw,
        json_extract_scalar(data, '$.satellite_data.cloud_coverage_pct') AS cloud_coverage_pct_raw,
        json_extract_scalar(data, '$.satellite_data.imagery_date') AS imagery_date_raw,
        json_extract_scalar(data, '$.satellite_data.data_quality') AS data_quality,
        json_extract_scalar(data, '$.satellite_data.fallback_weeks') AS fallback_weeks_raw,
        -- Metadata
        json_extract_scalar(data, '$.bbox.west') AS bbox_west,
        json_extract_scalar(data, '$.bbox.south') AS bbox_south,
        json_extract_scalar(data, '$.bbox.east') AS bbox_east,
        json_extract_scalar(data, '$.bbox.north') AS bbox_north,
        json_extract_scalar(data, '$.coordinates.lat') AS latitude,
        json_extract_scalar(data, '$.coordinates.lon') AS longitude,
        _file_modified_time AS source_file_timestamp
    FROM {{ source('raw', 'satellite_changes_json') }}
    WHERE json_extract_scalar(data, '$.region_name') IS NOT NULL
),

cleaned_data AS (
    SELECT
        -- Primary keys
        region_name,
        CAST(analysis_date_raw AS DATE) AS analysis_date,
        
        -- Satellite metrics (type casting and validation)
        CAST(vegetation_loss_pixels_raw AS BIGINT) AS vegetation_loss_pixels,
        CAST(construction_activity_pct_raw AS DOUBLE) AS construction_activity_pct,
        CAST(bare_soil_expansion_m2_raw AS DOUBLE) AS bare_soil_expansion_m2,
        CAST(total_changes_raw AS BIGINT) AS total_changes,
        CAST(area_affected_m2_raw AS DOUBLE) AS area_affected_m2,
        CAST(cloud_coverage_pct_raw AS DOUBLE) AS cloud_coverage_pct,
        
        -- Data quality indicators
        data_quality,
        CAST(fallback_weeks_raw AS INT) AS fallback_weeks_used,
        CAST(imagery_date_raw AS DATE) AS imagery_date,
        
        -- Geospatial metadata
        CAST(bbox_west AS DOUBLE) AS bbox_west,
        CAST(bbox_south AS DOUBLE) AS bbox_south,
        CAST(bbox_east AS DOUBLE) AS bbox_east,
        CAST(bbox_north AS DOUBLE) AS bbox_north,
        CAST(latitude AS DOUBLE) AS latitude,
        CAST(longitude AS DOUBLE) AS longitude,
        
        -- Audit columns
        source_file_timestamp,
        CURRENT_TIMESTAMP AS loaded_at
        
    FROM source_data
    WHERE CAST(total_changes_raw AS BIGINT) >= 0  -- Filter invalid data
)

SELECT
    *,
    -- Calculated fields
    CASE
        WHEN fallback_weeks_used = 0 THEN 'current_week'
        WHEN fallback_weeks_used <= 2 THEN 'recent'
        WHEN fallback_weeks_used <= 4 THEN 'fallback'
        ELSE 'stale'
    END AS data_freshness_category,
    
    CASE
        WHEN cloud_coverage_pct < 20 THEN 'excellent'
        WHEN cloud_coverage_pct < 50 THEN 'good'
        WHEN cloud_coverage_pct < 80 THEN 'acceptable'
        ELSE 'poor'
    END AS imagery_quality_tier

FROM cleaned_data
