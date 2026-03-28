{% macro generate_schema_name(custom_schema_name, node) -%}
/*
Macro: generate_schema_name
Custom schema naming logic for dbt models.
Creates schemas like: analytics_prod_staging, analytics_prod_marts

Args:
    custom_schema_name: Schema name from model config (staging, intermediate, marts)
    node: dbt node object

Returns:
    Full schema name including target schema prefix

Example in model config:
    {{ config(schema='staging') }}
    Results in: analytics_prod_staging (in prod target)
*/

    {%- set default_schema = target.schema -%}
    
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    
    {%- elif target.name == 'prod' -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    
    {%- elif target.name == 'dev' -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}_{{ target.user }}
    
    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    
    {%- endif -%}

{%- endmacro %}
