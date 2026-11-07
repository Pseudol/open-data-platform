FROM apache/airflow:2.10.2
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends libexpat1 \
 && rm -rf /var/lib/apt/lists/*
USER airflow
ARG AIRFLOW_VERSION=2.10.2
RUN PYV="$(python -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')" \
 && pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYV}.txt" \
    rasterio shapely pystac-client pandas pyarrow numpy