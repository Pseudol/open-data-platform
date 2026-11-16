"""Load raw agri Parquet from object storage into Postgres, idempotent by date."""
import argparse
import io
import os

import boto3
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

COLUMNS = [
    "field_id", "province", "acq_date", "scene_id", "mgrs_tile",
    "scene_cloud_cover", "total_pixels", "valid_pixels",
    "ndvi_mean", "gcvi_mean", "ndwi_mean",
]

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.agri_field_index (
    field_id text NOT NULL,
    province text,
    acq_date date NOT NULL,
    scene_id text,
    mgrs_tile text,
    scene_cloud_cover double precision,
    total_pixels integer,
    valid_pixels integer,
    ndvi_mean double precision,
    gcvi_mean double precision,
    ndwi_mean double precision,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (field_id, acq_date)
);
"""


def make_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
    )


def list_partitions(s3, start, end):
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket="lake", Prefix="raw/agri/"):
        for obj in page.get("Contents", []):
            d = obj["Key"].split("dt=")[1].split("/")[0]
            if start <= d <= end:
                keys.append((d, obj["Key"]))
    return sorted(keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    s3 = make_s3_client()
    parts = list_partitions(s3, args.start, args.end)
    if not parts:
        print("no partitions in range, nothing to load")
        return

    frames = []
    for _, key in parts:
        body = s3.get_object(Bucket="lake", Key=key)["Body"].read()
        frames.append(pd.read_parquet(io.BytesIO(body)))
    df = pd.concat(frames, ignore_index=True)[COLUMNS]
    df["acq_date"] = pd.to_datetime(df["acq_date"]).dt.date
    df = df.astype(object).where(pd.notna(df), None)
    rows = list(df.itertuples(index=False, name=None))
    dates = sorted({r[2] for r in rows})

    conn = psycopg2.connect(
        host=os.environ["WAREHOUSE_HOST"],
        dbname=os.environ["WAREHOUSE_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    try:
        with conn, conn.cursor() as cur:  # one transaction: all or nothing
            cur.execute(DDL)
            cur.execute("DELETE FROM raw.agri_field_index WHERE acq_date = ANY(%s)", (dates,))
            execute_values(
                cur,
                f"INSERT INTO raw.agri_field_index ({', '.join(COLUMNS)}) VALUES %s",
                rows,
            )
    finally:
        conn.close()
    print(f"loaded {len(rows)} rows for {len(dates)} dates")


if __name__ == "__main__":
    main()