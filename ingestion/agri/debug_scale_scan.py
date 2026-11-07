import numpy as np
import rasterio
from pystac_client import Client

c = Client.open("https://earth-search.aws.element84.com/v1")
bboxes = {"chinhoyi": [30.0, -17.6, 30.5, -17.1], "marondera": [31.3, -18.4, 31.8, -17.9]}
seen = set()
for name, bbox in bboxes.items():
    items = c.search(collections=["sentinel-2-l2a"], bbox=bbox,
                     datetime="2025-12-01T00:00:00Z/2025-12-10T23:59:59Z").items()
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        with rasterio.open(item.assets["red"].href) as src:
            a = src.read(1, out_shape=(200, 200))  # low-res overview of whole tile
        a = a[a > 0]
        print(item.id, item.properties.get("s2:processing_baseline"),
              "p5:", int(np.percentile(a, 5)), "median:", int(np.median(a)))