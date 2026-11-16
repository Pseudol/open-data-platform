from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.operators.bash import BashOperator


@dag(
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["agri", "raw"],
)
def agri_raw_ingest():
    window = "--start {{ macros.ds_add(ds, -5) }} --end {{ ds }}"
    extract = BashOperator(
        task_id="extract_sentinel2",
        bash_command=f"python /opt/airflow/ingestion/agri/extract.py {window} --sink s3",
    )
    load = BashOperator(
        task_id="load_raw_postgres",
        bash_command=f"python /opt/airflow/ingestion/agri/load_raw.py {window}",
    )
    extract >> load


agri_raw_ingest()