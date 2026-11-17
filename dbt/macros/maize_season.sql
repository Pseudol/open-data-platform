{% macro maize_season_start_year(date_col) %}
    case
        when extract(month from {{ date_col }}) >= 11
            then extract(year from {{ date_col }})::int
        when extract(month from {{ date_col }}) <= 6
            then extract(year from {{ date_col }})::int - 1
    end
{% endmacro %}