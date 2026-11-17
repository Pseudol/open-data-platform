with spine as (

    select d::date as date_day
    from generate_series(
        '{{ var("calendar_start") }}'::date,
        '{{ var("calendar_end") }}'::date,
        interval '1 day'
    ) as d

),

seasoned as (

    select
        date_day,
        {{ maize_season_start_year('date_day') }} as season_start_year
    from spine

)

select
    date_day,
    season_start_year,
    case
        when season_start_year is not null
        then season_start_year::text || '/' || right((season_start_year + 1)::text, 2)
        else 'Off-season'
    end as season_label,
    season_start_year is not null as is_growing_season
from seasoned