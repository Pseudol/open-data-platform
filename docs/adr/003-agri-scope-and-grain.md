# ADR-003: Agri product scope and grain
Status: accepted
Scope: 20 sample maize fields, Mashonaland East and West, Zimbabwe.
Source: Sentinel-2 L2A via Earth Search STAC API (no API key).
Season window: 1 Nov to 30 Jun (crosses the calendar year; season labelled by start year).
Grain: one row per field, per acquisition date, per index (NDVI, GCVI, NDWI).
Why 20 fields: keeps compute small while still showing partitioning, SCD2 and backfills.