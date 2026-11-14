# ADR-004: Sentinel-2 extraction rules

Status: accepted (verified on baselines 05.11, December 2025, and 05.12, April 2026)
Early-season scenes (December 2025) verified.
Date: 2026-11
Relates to: ADR-003 (scope and grain)

## Context
The agri product turns Sentinel-2 L2A scenes into one vegetation-index
record per field per acquisition date. Scenes overlap, clouds and shadows
are common in the maize season, and reads over the network sometimes fail.
The extraction rules decide what the raw layer contains, so they must be
explicit and reproducible.

## Decisions

1. **Valid pixels.** A pixel counts only if it lies inside the field polygon
   and its scene classification (SCL) value is 4 (vegetation) or 5 (bare
   soil). Cloud, shadow, water, snow and saturated pixels are excluded.
2. **Common grid.** SCL and SWIR are 20 m bands. They are resampled to the
   10 m grid with nearest-neighbour so every band is compared pixel by pixel.
3. **Reflectance.** Reflectance = DN x 0.0001, and DN 0 is nodata. The
   catalogue advertises an extra offset of -0.1, but raw pixel values in
   baseline 05.12 scenes do not carry the matching +1000 offset (red 5th
   percentile 209-376 across 15 scenes, April 2026). Applying the catalogue
   offset produced negative reflectance and invalid indices, so it is not
   applied. See "Incident" below. An end-to-end December run passed the sanity gate with NDVI 0.21 to 0.55.
4. **Indices.**
   - NDVI = (NIR - Red) / (NIR + Red)
   - GCVI = NIR / Green - 1
   - NDWI = (NIR - SWIR16) / (NIR + SWIR16), the Gao form, chosen for
     canopy water content. The McFeeters form (Green/NIR) is not used.
   Each field-date value is the mean over its valid pixels.
5. **Overlapping and reprocessed scenes.** Several scenes can cover a field on
   one day, including reprocessed copies of the same tile (IDs ending _0 and
   _1). The scene with the most valid pixels is kept, with ties broken by the
   higher scene ID, so the choice is deterministic.
6. **Quality is recorded, not hidden.** Every row stores total_pixels and
   valid_pixels. Fully clouded field-dates are kept with null indices, so
   downstream models decide what counts as usable.
7. **All-or-nothing runs.** Each read is retried up to three times. If any
   read still fails, the run writes nothing and exits with an error, so a
   partition never depends on how the network behaved.
8. **Idempotent output.** Each acquisition date is one object,
   `raw/agri/dt=YYYY-MM-DD/part-0.parquet`, overwritten on every run.
   Re-running any date range gives the same result.
9. **Sanity gate.** Before writing, the run fails if any NDVI falls outside
   -1 to 1 or any GCVI is below -1. Nothing is written when the gate fires.

## Incident: reflectance scaling (found during development)
The first implementation trusted the catalogue's scale and offset. Output
looked wrong: NDVI values from -4,974 to infinity, GCVI down to -574,085.
Pixel statistics showed red and green medians near 500 DN, below the 1000
floor the offset implies, so subtracting 0.1 made reflectance negative and
the ratios exploded near zero. A scan of all scenes in the window confirmed
the pattern. The fix was rule 3 plus the sanity gate (rule 9), so a repeat
fails loudly instead of producing plausible-looking bad data.

## Consequences
- Re-running or backfilling is safe, which allows a rolling lookback window
  to catch late-arriving scenes.
- Raw data stays faithful to the satellite product. Cloud thresholds and
  smoothing belong in the dbt layer.
- A transient failure blocks the run until it is retried. This is accepted
  to avoid silent, non-reproducible data.
- Extraction runs in a container because host-installed geo libraries
  (PostGIS/PROJ) and the Windows TLS stack caused failures on Windows.

## Alternatives considered
- Writing partial results when reads fail: rejected, not reproducible.
- Filtering by scene-level cloud cover only: rejected, pixel-level masking
  keeps usable fields from cloudy scenes.
- Trusting catalogue metadata blindly: rejected after the incident above.

