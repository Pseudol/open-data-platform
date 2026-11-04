import os
from datetime import datetime

import boto3
import psycopg2
from airflow.decorators import dag, task


@dag(start_date=datetime(2024, 1, 1), schedule=None, catchup=False)
def smoke_test():
    @task
    def write_to_minio():
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["MINIO_ENDPOINT"],
            aws_access_key_id=os.environ["MINIO_ROOT_USER"],
            aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        )
        if "lake" not in [b["Name"] for b in s3.list_buckets()["Buckets"]]:
            s3.create_bucket(Bucket="lake")
        s3.put_object(Bucket="lake", Key="smoke/hello.txt", Body=b"platform works")

    @task
    def write_to_postgres():
        conn = psycopg2.connect(
            host=os.environ["WAREHOUSE_HOST"],
            dbname=os.environ["WAREHOUSE_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
        )
        with conn, conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS smoke (ts timestamptz default now(), msg text)")
            cur.execute("INSERT INTO smoke (msg) VALUES ('platform works')")

    write_to_minio() >> write_to_postgres()


smoke_test()
