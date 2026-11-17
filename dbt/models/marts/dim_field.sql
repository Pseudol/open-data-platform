select
    {{ dbt_utils.generate_surrogate_key(['field_id']) }} as field_key,
    field_id,
    max(province) as province
from {{ ref('stg_agri_field_index') }}
group by field_id