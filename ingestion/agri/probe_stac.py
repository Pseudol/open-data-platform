from pystac_client import Client

client = Client.open("https://earth-search.aws.element84.com/v1")

areas = {
    "chinhoyi": [30.0, -17.6, 30.5, -17.1],
    "marondera": [31.3, -18.4, 31.8, -17.9],
}

for name, bbox in areas.items():
    search = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime="2025-11-01/2026-06-30",
        query={"eo:cloud_cover": {"lt": 30}},
    )
    items = list(search.items())
    print(name, len(items), "scenes")
    if items:
        print("  assets:", sorted(items[0].assets.keys())[:12])
        print("  first:", items[0].datetime)