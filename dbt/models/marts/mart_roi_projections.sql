{{
  config(
    materialized='table',
    tags=['marts', 'financial', 'forecasts']
  )
}}

/*
Mart: ROI Projections
Financial forecasting and scenario analysis for investment decisions.
Monte Carlo-inspired confidence intervals and risk-adjusted returns.

Target audience: CFO, finance team, investors
Update frequency: Weekly (after Step Functions run)
*/

WITH latest_performance AS (
    SELECT *
    FROM {{ ref('mart_region_performance') }}
    WHERE is_current_week = TRUE
),

roi_scenarios AS (
    SELECT
        region_name,
        analysis_date,
        
        -- Base case (current projection)
        projected_roi_3yr_pct AS base_roi_3yr,
        estimated_investment_usd AS base_investment,
        total_estimated_profit_usd AS base_profit,
        payback_period_years AS base_payback,
        
        -- Bull case (optimistic: +30% ROI improvement)
        projected_roi_3yr_pct * 1.30 AS bull_roi_3yr,
        estimated_investment_usd AS bull_investment,
        total_estimated_profit_usd * 1.30 AS bull_profit,
        payback_period_years * 0.77 AS bull_payback,  -- Faster payback
        
        -- Bear case (pessimistic: -30% ROI degradation)
        projected_roi_3yr_pct * 0.70 AS bear_roi_3yr,
        estimated_investment_usd AS bear_investment,
        total_estimated_profit_usd * 0.70 AS bear_profit,
        payback_period_years * 1.43 AS bear_payback,  -- Slower payback
        
        -- Risk metrics
        risk_category,
        composite_confidence_score,
        financial_confidence_score,
        
        -- Market conditions
        market_momentum,
        investment_trend,
        price_trend_30d_pct,
        
        -- Current metrics
        final_investment_score,
        investment_recommendation,
        recommended_plot_size_m2,
        current_land_value_per_m2_usd,
        projected_value_3yr_per_m2_usd,
        land_appreciation_3yr_pct
        
    FROM latest_performance
),

risk_adjusted_returns AS (
    SELECT
        *,
        -- Risk-adjusted ROI (base case * confidence * inverse risk)
        base_roi_3yr * composite_confidence_score * 
        CASE risk_category
            WHEN 'low' THEN 1.0
            WHEN 'medium' THEN 0.85
            WHEN 'high' THEN 0.70
            WHEN 'speculative' THEN 0.50
            ELSE 0.80
        END AS risk_adjusted_roi_3yr,
        
        -- Expected value (probability-weighted returns)
        -- Assumes: Bull 25%, Base 50%, Bear 25% probability
        (bull_profit * 0.25) + (base_profit * 0.50) + (bear_profit * 0.25) AS expected_profit_usd,
        
        -- Sharpe ratio proxy (excess return per unit of volatility)
        -- Using score volatility as risk measure
        CASE 
            WHEN score_volatility > 0 
            THEN (base_roi_3yr - 0.05) / (score_volatility / 100.0)  -- Assuming 5% risk-free rate
            ELSE NULL
        END AS sharpe_ratio_proxy,
        
        -- Profit margin
        CASE 
            WHEN base_investment > 0 
            THEN (base_profit / base_investment) * 100.0 
            ELSE NULL 
        END AS profit_margin_pct
        
    FROM roi_scenarios
)

SELECT
    region_name,
    analysis_date,
    
    -- Investment sizing
    recommended_plot_size_m2,
    base_investment AS required_investment_usd,
    
    -- Base case projections
    base_roi_3yr AS projected_roi_3yr_pct,
    base_profit AS projected_profit_usd,
    base_payback AS payback_period_years,
    
    -- Scenario analysis
    bull_roi_3yr AS bull_case_roi_3yr_pct,
    bull_profit AS bull_case_profit_usd,
    bull_payback AS bull_case_payback_years,
    
    bear_roi_3yr AS bear_case_roi_3yr_pct,
    bear_profit AS bear_case_profit_usd,
    bear_payback AS bear_case_payback_years,
    
    expected_profit_usd,
    
    -- Risk-adjusted metrics
    risk_adjusted_roi_3yr AS risk_adjusted_roi_3yr_pct,
    risk_category,
    composite_confidence_score,
    sharpe_ratio_proxy,
    
    -- Land valuation
    current_land_value_per_m2_usd,
    projected_value_3yr_per_m2_usd,
    land_appreciation_3yr_pct,
    
    -- Market context
    final_investment_score,
    investment_recommendation,
    market_momentum,
    investment_trend,
    price_trend_30d_pct,
    
    -- Financial ratios
    profit_margin_pct,
    
    -- ROI confidence intervals
    LEAST(bull_roi_3yr, base_roi_3yr * 1.5) AS roi_upper_bound_95pct,
    GREATEST(bear_roi_3yr, base_roi_3yr * 0.5) AS roi_lower_bound_95pct,
    (bull_roi_3yr - bear_roi_3yr) AS roi_range_spread,
    
    -- Investment priority score (combines ROI, confidence, risk)
    (risk_adjusted_roi_3yr * 100) * 
    composite_confidence_score * 
    (final_investment_score / 100.0) AS investment_priority_score,
    
    -- Recommendation with risk context
    CONCAT(
        investment_recommendation,
        ' (',
        CASE risk_category
            WHEN 'low' THEN 'Low Risk'
            WHEN 'medium' THEN 'Moderate Risk'
            WHEN 'high' THEN 'High Risk'
            WHEN 'speculative' THEN 'Speculative'
            ELSE 'Unknown Risk'
        END,
        ', ',
        CAST(ROUND(composite_confidence_score * 100, 0) AS VARCHAR),
        '% confidence)'
    ) AS detailed_recommendation

FROM risk_adjusted_returns
ORDER BY investment_priority_score DESC
