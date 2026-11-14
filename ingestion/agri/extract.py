"""Extract per-field vegetation indices from Sentinel-2 L2A (Earth Search STAC).

Grain: one row per field per acquisition date.
Idempotent: partition dt=YYYY-MM-DD is fully rewritten on every run.
Indices: NDVI=(nir-red)/(nir+red), GCVI=nir/green-1, NDWI=(nir-swir16)/(nir+swir16)
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.features import geometry_mask, geometry_window
from rasterio.warp import transform_geom
from rasterio.windows import bounds as window_bounds
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape
import time

STAC_URL = "https://earth-search.aws.element84.com/v1"
FIELDS_PATH = Path(__file__).parent / "fields.geojson"
VALID_SCL = (4, 5)  # vegetation, bare soil; clouds, shadow, water, snow excluded
GDAL_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    GDAL_HTTP_MAX_RETRY="4",
    GDAL_HTTP_RETRY_DELAY="3",
    GDAL_HTTP_TIMEOUT="60",
)


def load_fields():
    with open(FIELDS_PATH, encoding="utf-8") as f:
        gj = json.load(f)
    return [
        {
            "field_id": ft["properties"]["field_id"],
            "province": ft["properties"].get("province"),
            "geom": shape(ft["geometry"]),
        }
        for ft in gj["features"]
    ]


def read_aligned(asset, bounds, out_shape):
    """Read an asset over `bounds`, resampled to `out_shape` (nearest)."""
    with rasterio.open(asset.href) as src:
        win = from_bounds(*bounds, transform=src.transform)
        return src.read(1, window=win, out_shape=out_shape, resampling=Resampling.nearest)


def reflectance(asset, bounds, out_shape):
    dn = read_aligned(asset, bounds, out_shape).astype("float32")
    ref = dn * 0.0001  # catalogue offset not applied: pixel values do not carry it
    ref[dn == 0] = np.nan  # 0 = nodata
    return ref


def field_row(item, field):
    red_asset = item.assets["red"]
    with rasterio.open(red_asset.href) as src:
        geom = transform_geom("EPSG:4326", src.crs, mapping(field["geom"]))
        win = geometry_window(src, [geom])
        transform = src.window_transform(win)
        out_shape = (int(win.height), int(win.width))
        bounds = window_bounds(win, src.transform)

    red = reflectance(red_asset, bounds, out_shape)
    inside = geometry_mask([geom], out_shape=out_shape, transform=transform, invert=True)
    nir = reflectance(item.assets["nir"], bounds, out_shape)
    green = reflectance(item.assets["green"], bounds, out_shape)
    swir = reflectance(item.assets["swir16"], bounds, out_shape)
    scl = read_aligned(item.assets["scl"], bounds, out_shape)

    valid = (
        inside
        & np.isin(scl, VALID_SCL)
        & np.isfinite(red) & np.isfinite(nir) & np.isfinite(green) & np.isfinite(swir)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
        gcvi = nir / green - 1
        ndwi = (nir - swir) / (nir + swir)

    def mean(a):
        return float(np.nanmean(a[valid])) if valid.any() else np.nan

    return {
        "field_id": field["field_id"],
        "province": field["province"],
        "acq_date": item.datetime.date().isoformat(),
        "scene_id": item.id,
        "mgrs_tile": item.properties.get("grid:code"),
        "scene_cloud_cover": item.properties.get("eo:cloud_cover"),
        "total_pixels": int(inside.sum()),
        "valid_pixels": int(valid.sum()),
        "ndvi_mean": mean(ndvi),
        "gcvi_mean": mean(gcvi),
        "ndwi_mean": mean(ndwi),
    }

def with_retries(fn, attempts=3, base_delay=5):
    for n in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if n == attempts:
                raise
            print(f"retry {n}/{attempts - 1} after {exc!r}")
            time.sleep(base_delay * n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", default="data/raw/agri")
    ap.add_argument("--max-cloud", type=float, default=80)
    args = ap.parse_args()

    client = Client.open(STAC_URL)
    best = {}
    failures = []
    with rasterio.Env(**GDAL_ENV):
        for field in load_fields():
            search = client.search(
                collections=["sentinel-2-l2a"],
                intersects=mapping(field["geom"]),
                datetime=f"{args.start}T00:00:00Z/{args.end}T23:59:59Z",
                query={"eo:cloud_cover": {"lt": args.max_cloud}},
            )
            for item in search.items():
                try:
                    row = with_retries(lambda: field_row(item, field))
                except Exception as exc:
                    failures.append((field["field_id"], item.id, repr(exc)))
                    print(f"FAIL {field['field_id']} {item.id}: {exc!r}")
                    continue
                key = (row["field_id"], row["acq_date"])
                if key not in best or (row["valid_pixels"], row["scene_id"]) > (
                    best[key]["valid_pixels"], best[key]["scene_id"]
                ):
                    best[key] = row
            print(f"done {field['field_id']}")

    if failures:
        print(f"{len(failures)} item(s) failed after retries, nothing written:")
        for f in failures:
            print("  ", f)
        raise SystemExit(1)

    bad = [
        r for r in best.values()
        if (pd.notna(r["ndvi_mean"]) and not -1 <= r["ndvi_mean"] <= 1)
        or (pd.notna(r["gcvi_mean"]) and r["gcvi_mean"] < -1)
    ]
    if bad:
        print(f"{len(bad)} rows outside valid index range, nothing written, e.g.:", bad[0])
        raise SystemExit(1)

    by_date = defaultdict(list)
    for (_, d), row in best.items():
        by_date[d].append(row)
    for d, rows in sorted(by_date.items()):
        out_dir = Path(args.out) / f"dt={d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).sort_values("field_id").to_parquet(out_dir / "part-0.parquet", index=False)
        print(f"wrote dt={d}: {len(rows)} fields")


if __name__ == "__main__":
    main()