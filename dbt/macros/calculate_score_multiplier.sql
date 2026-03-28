{% macro calculate_score_multiplier(score_value, min_score=0, max_score=100, min_multiplier=0.8, max_multiplier=1.3) %}
/*
Macro: calculate_score_multiplier
Converts a numeric score (0-100) into a multiplier for investment scoring.
Mirrors the CloudClearingAPI scoring logic.

Args:
    score_value: The score to convert (0-100)
    min_score: Minimum score value (default: 0)
    max_score: Maximum score value (default: 100)
    min_multiplier: Multiplier for min score (default: 0.8)
    max_multiplier: Multiplier for max score (default: 1.3)

Returns:
    A multiplier value between min_multiplier and max_multiplier

Example:
    {{ calculate_score_multiplier('infrastructure_score') }}
*/

CASE
    WHEN {{ score_value }} IS NULL THEN 1.0
    WHEN {{ score_value }} < {{ min_score }} THEN {{ min_multiplier }}
    WHEN {{ score_value }} > {{ max_score }} THEN {{ max_multiplier }}
    ELSE 
        {{ min_multiplier }} + 
        (({{ score_value }} - {{ min_score }}) / ({{ max_score }} - {{ min_score }}) * 
        ({{ max_multiplier }} - {{ min_multiplier }}))
END

{% endmacro %}
