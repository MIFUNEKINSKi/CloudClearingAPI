{% macro audit_columns() %}
/*
Macro: audit_columns
Adds standard audit columns to models for data lineage tracking.

Returns:
    SQL fragment with timestamp columns

Example:
    SELECT
        *,
        {{ audit_columns() }}
    FROM source_table
*/

CURRENT_TIMESTAMP AS dbt_loaded_at,
'{{ invocation_id }}' AS dbt_invocation_id,
'{{ this }}' AS dbt_model_name,
'{{ run_started_at }}' AS dbt_run_started_at

{% endmacro %}
