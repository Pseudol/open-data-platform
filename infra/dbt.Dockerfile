FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dbt-core==1.12.7 dbt-postgres==1.9.1

WORKDIR /usr/app/dbt
ENTRYPOINT ["dbt"]