{% macro investment_recommendation(score_column) %}
/*
Macro: investment_recommendation
Generates BUY/WATCH/PASS recommendation based on investment score.
Matches CloudClearingAPI's thresholds.

Args:
    score_column: Column name containing final investment score (0-100)

Returns:
    SQL CASE statement returning recommendation

Example:
    {{ investment_recommendation('final_investment_score') }}
*/

CASE
    WHEN {{ score_column }} >= 70 THEN 'BUY'
    WHEN {{ score_column }} >= 50 THEN 'WATCH'
    WHEN {{ score_column }} >= 0 THEN 'PASS'
    ELSE 'UNKNOWN'
END

{% endmacro %}
