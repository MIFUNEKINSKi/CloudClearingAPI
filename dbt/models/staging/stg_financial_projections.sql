{{
  config(
    materialized='view',
    tags=['staging', 'financial']
  )
}}

/*
Staging model for financial projections calculated by FinancialMetricsEngine.
Contains ROI forecasts, land valuations, and development cost estimates.

Source: s3://cloudclearing-data-lake/raw/financial_projections/
Update frequency: Weekly (Monday 6am UTC via Step Functions)
*/

WITH source_data AS (
    SELECT
        json_extract_scalar(data, '$.region_name') AS region_name,
        json_extract_scalar(data, '$.analysis_date') AS analysis_date_raw,
        json_extract_scalar(data, '$.financial_projection.current_land_value_per_m2') AS current_land_value_per_m2_raw,
        json_extract_scalar(data, '$.financial_projection.projected_value_3yr_per_m2') AS projected_value_3yr_per_m2_raw,
        json_extract_scalar(data, '$.financial_projection.projected_roi_3yr') AS projected_roi_3yr_raw,
        json_extract_scalar(data, '$.financial_projection.recommended_plot_size_m2') AS recommended_plot_size_m2_raw,
        json_extract_scalar(data, '$.financial_projection.estimated_investment_idr') AS estimated_investment_idr_raw,
        json_extract_scalar(data, '$.financial_projection.development_cost_per_m2') AS development_cost_per_m2_raw,
        json_extract_scalar(data, '$.financial_projection.total_estimated_profit_idr') AS total_estimated_profit_idr_raw,
        json_extract_scalar(data, '$.financial_projection.payback_period_years') AS payback_period_years_raw,
        json_extract_scalar(data, '$.financial_projection.risk_category') AS risk_category,
        json_extract_scalar(data, '$.financial_projection.data_sources') AS data_sources_json,
        json_extract_scalar(data, '$.financial_projection.confidence_score') AS confidence_score_raw,
        _file_modified_time AS source_file_timestamp
    FROM {{ source('raw', 'financial_projections_json') }}
    WHERE json_extract_scalar(data, '$.region_name') IS NOT NULL
),

cleaned_data AS (
    SELECT
        -- Primary keys
        region_name,
        CAST(analysis_date_raw AS DATE) AS analysis_date,
        
        -- Land valuations (IDR per m²)
        CAST(current_land_value_per_m2_raw AS BIGINT) AS current_land_value_per_m2_idr,
        CAST(projected_value_3yr_per_m2_raw AS BIGINT) AS projected_value_3yr_per_m2_idr,
        
        -- ROI metrics
        CAST(projected_roi_3yr_raw AS DOUBLE) AS projected_roi_3yr_pct,
        CAST(payback_period_years_raw AS DOUBLE) AS payback_period_years,
        
        -- Investment sizing
        CAST(recommended_plot_size_m2_raw AS DOUBLE) AS recommended_plot_size_m2,
        CAST(estimated_investment_idr_raw AS BIGINT) AS estimated_investment_idr,
        
        -- Development costs
        CAST(development_cost_per_m2_raw AS BIGINT) AS development_cost_per_m2_idr,
        CAST(total_estimated_profit_idr_raw AS BIGINT) AS total_estimated_profit_idr,
        
        -- Risk assessment
        risk_category,  -- 'low', 'medium', 'high', 'speculative'
        CAST(confidence_score_raw AS DOUBLE) AS confidence_score,
        
        -- Data provenance
        data_sources_json,
        
        -- Audit columns
        source_file_timestamp,
        CURRENT_TIMESTAMP AS loaded_at
        
    FROM source_data
    WHERE CAST(projected_roi_3yr_raw AS DOUBLE) IS NOT NULL
)

SELECT
    *,
    -- Calculated fields
    CASE
        WHEN projected_roi_3yr_pct >= 0.50 THEN 'excellent'  -- >50% ROI
        WHEN projected_roi_3yr_pct >= 0.30 THEN 'strong'     -- 30-50% ROI
        WHEN projected_roi_3yr_pct >= 0.15 THEN 'moderate'   -- 15-30% ROI
        WHEN projected_roi_3yr_pct >= 0.05 THEN 'weak'       -- 5-15% ROI
        ELSE 'poor'                                          -- <5% ROI
    END AS roi_tier,
    
    CASE
        WHEN payback_period_years <= 2 THEN 'fast'
        WHEN payback_period_years <= 4 THEN 'moderate'
        WHEN payback_period_years <= 6 THEN 'slow'
        ELSE 'very_slow'
    END AS payback_speed,
    
    CASE
        WHEN confidence_score >= 0.80 THEN 'high_confidence'
        WHEN confidence_score >= 0.60 THEN 'medium_confidence'
        ELSE 'low_confidence'
    END AS confidence_tier,
    
    -- Currency conversions (1 USD = 15,700 IDR)
    CAST(current_land_value_per_m2_idr AS DOUBLE) / 15700.0 AS current_land_value_per_m2_usd,
    CAST(estimated_investment_idr AS DOUBLE) / 15700.0 AS estimated_investment_usd,
    CAST(total_estimated_profit_idr AS DOUBLE) / 15700.0 AS total_estimated_profit_usd,
    
    -- Value appreciation
    (CAST(projected_value_3yr_per_m2_idr AS DOUBLE) - CAST(current_land_value_per_m2_idr AS DOUBLE)) / 
        CAST(current_land_value_per_m2_idr AS DOUBLE) AS land_appreciation_3yr_pct

FROM cleaned_data
