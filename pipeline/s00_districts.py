"""Petersburg's districts (admin_level 5) from Overpass, with full geometry."""
import json

import requests

from .city import UA

Q = """[out:json][timeout:300];
relation["boundary"="administrative"]["admin_level"="5"](59.79,30.04,60.08,30.64);
out geom;"""
SERVERS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]


def main():
    for url in SERVERS:
        try:
            r = requests.post(url, data={"data": Q}, headers=UA, timeout=400)
            r.raise_for_status()
            d = r.json()
            break
        except Exception as e:  # busy server: try the next mirror
            print(url, e)
    json.dump(d, open("data/raw/districts.json", "w"))
    print([e["tags"].get("name") for e in d["elements"]])


if __name__ == "__main__":
    main()
