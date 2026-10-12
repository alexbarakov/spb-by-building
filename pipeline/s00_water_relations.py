"""Water multipolygons (rivers, harbours, the Neva) straight from Overpass with full member geometry.

The BBBike extract cuts relations at its box, and GDAL drops a multipolygon whose ring does not close,
which loses the Neva itself. Overpass returns every member way whole.
"""
import json

import requests

from .city import UA

Q = """[out:json][timeout:300];
(relation["natural"="water"](59.79,30.04,60.08,30.64);
 relation["waterway"="riverbank"](59.79,30.04,60.08,30.64);
 relation["natural"="bay"](59.79,30.04,60.08,30.64););
out geom;"""


def main():
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": Q}, headers=UA, timeout=400)
    r.raise_for_status()
    d = r.json()
    json.dump(d, open("data/raw/water_relations.json", "w"))
    print(len(d["elements"]), "relations")


if __name__ == "__main__":
    main()
