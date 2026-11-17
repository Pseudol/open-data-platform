-- depends_on: {{ ref('dim_field') }}
-- depends_on: {{ ref('dim_date') }}



select
    {{ dbt_utils.generate_surrogate_key(['field_id', 'observation_date']) }}
                                             as field_index_key,
    {{ dbt_utils.generate_surrogate_key(['field_id']) }}
                                             as field_key,
    to_char(observation_date, 'YYYYMMDD')::int
                                             as date_key,
    scene_id,
    mgrs_tile,
    scene_cloud_cover_pct,
    total_pixels,
    valid_pixels,
    valid_pixel_share,
    is_usable,
    ndvi_mean,
    gcvi_mean,
    ndwi_mean,
    loaded_at
from {{ ref('stg_agri_field_index') }}