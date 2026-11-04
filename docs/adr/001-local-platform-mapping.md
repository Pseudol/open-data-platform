# ADR-001: Local open-source platform and cloud mapping
Status: accepted
Decision: Postgres + MinIO + Airflow in Docker Compose.
Why: reproducible by any reviewer with one command; zero cloud cost.
Cloud mapping: MinIO = S3/ADLS, Postgres = RDS/Redshift, Airflow = ADF/MWAA.