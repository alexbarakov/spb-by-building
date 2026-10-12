"""Everything that is Saint Petersburg rather than the engine."""
from pyproj import Transformer

NAME = "spb"
LABEL = "Петербург"
CRS = 32636  # UTM 36N, metres
TO_CRS = Transformer.from_crs(4326, CRS, always_xy=True)
# Local frame origin: Palace Square, the Alexander Column.
ORIGIN = TO_CRS.transform(30.3159, 59.9391)
OSM = "data/raw/spb.osm.pbf"
UA = {"User-Agent": "spb-by-building/0.1 (https://stop-token.com/lab/)"}
