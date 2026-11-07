import numpy as np
import rasterio
from pystac_client import Client

c = Client.open("https://earth-search.aws.element84.com/v1")
item = next(c.search(collections=["sentinel-2-l2a"], ids=["S2A_36KTF_20260407_0_L2A"]).items())
print("baseline:", item.properties.get("s2:processing_baseline"))
for k in ("red", "green", "nir", "swir16"):
    a = item.assets[k]
    print(k, "catalogue:", a.extra_fields.get("raster:bands"))
    with rasterio.open(a.href) as src:
        data = src.read(1, window=((5000, 5100), (5000, 5100)))
        print("  DN min/median/max:", data.min(), int(np.median(data)), data.max())
        print("  file scales/offsets:", src.scales, src.offsets, "nodata:", src.nodata)