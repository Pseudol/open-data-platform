with source as (

    select * from {{ source('raw', 'agri_field_index') }}

),

renamed as (

    select
        field_id,
        province,
        acq_date                    as observation_date,
        scene_id,
        mgrs_tile,
        scene_cloud_cover           as scene_cloud_cover_pct,
        total_pixels,
        valid_pixels,
        ndvi_mean,
        gcvi_mean,
        ndwi_mean,
        loaded_at
    from source

),

final as (

    select
        *,
        case
            when total_pixels > 0
            then valid_pixels::numeric / total_pixels
        end as valid_pixel_share
    from renamed

)

select
    *,
    coalesce(
        valid_pixel_share >= {{ var('min_valid_share') }}
        and ndvi_mean is not null,
        false
    ) as is_usable
from final