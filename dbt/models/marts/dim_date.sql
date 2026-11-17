select
    to_char(date_day, 'YYYYMMDD')::int       as date_key,
    date_day                                 as full_date,
    extract(year from date_day)::int         as year,
    extract(month from date_day)::int        as month,
    to_char(date_day, 'FMMonth')             as month_name,
    extract(isodow from date_day)::int       as day_of_week,
    season_start_year,
    season_label,
    is_growing_season
from {{ ref('int_date_season') }}