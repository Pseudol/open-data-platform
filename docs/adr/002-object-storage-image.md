# ADR-002: Object storage image after MinIO withdrew its public images
Status: accepted
Context: minio/minio was removed from Docker Hub and Quay in Sept 2026.
Decision: use an S3-compatible fork (pgsty/silo), pinned to an exact tag.
Why safe: all code uses the S3 API via boto3, so the storage engine is swappable.
Consequence: ADR-001 cloud mapping (S3/ADLS) is unchanged. Re-evaluate if the fork stalls.