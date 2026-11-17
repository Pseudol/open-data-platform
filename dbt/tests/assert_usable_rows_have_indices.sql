-- a row flagged usable must carry all three indices
select *
from {{ ref('fct_field_index') }}
where is_usable
  and (ndvi_mean is null or gcvi_mean is null or ndwi_mean is null)