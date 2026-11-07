FROM python:3.11-slim
RUN pip install --no-cache-dir rasterio shapely pandas pyarrow numpy pystac-client
RUN apt-get update \
 && apt-get install -y --no-install-recommends libexpat1 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app