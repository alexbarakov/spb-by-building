"""Water and land in the local frame, from OSM: lakes, rivers and canals (natural=water) and the
Gulf of Finland, rebuilt from the coastline inside the extract's box.

water.bin / land.bin layout (little-endian):
  u32 nPoly, nRing, nVert; u32 ringStart[nPoly+1]; u32 vertStart[nRing+1]; f32 xz[2*nVert]
"""
import struct
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
import shapely
from shapely.geometry import Point, box

from .city import CRS, OSM, TO_CRS
from .s03_tiles import to_local

OUT = Path("web/data")
# Points known to be open water of the Neva Bay; a coastline face containing one is sea.
SEA_SEEDS = [(30.10, 59.93)]


def polygons(geom):
    return [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon" and not g.is_empty]


def pack(geoms) -> bytes:
    ring_start, vert_start, verts = [0], [0], []
    for poly in geoms:
        for ring in [poly.exterior, *poly.interiors]:
            c = shapely.get_coordinates(ring)[:-1]
            if len(c) < 3:
                continue
            verts.append(to_local(c).astype("<f4"))
            vert_start.append(vert_start[-1] + len(c))
        ring_start.append(len(vert_start) - 1)
    V = np.concatenate(verts)
    return (struct.pack("<3I", len(ring_start) - 1, len(vert_start) - 1, len(V))
            + np.array(ring_start, "<u4").tobytes() + np.array(vert_start, "<u4").tobytes() + V.tobytes())


def main():
    info = pyogrio.read_info(OSM, layer="multipolygons")
    x0, y0, x1, y1 = 30.0411, 59.7931, 30.6311, 60.0728  # the BBBike extract's box
    area = gpd.GeoSeries([box(x0, y0, x1, y1)], crs=4326).to_crs(CRS).iloc[0]

    mp = pyogrio.read_dataframe(OSM, layer="multipolygons", columns=["natural", "other_tags"])
    tags = mp.other_tags.fillna("")
    water = mp[(mp.natural == "water") | tags.str.contains('"water"=>"(river|canal)"|"waterway"=>"riverbank"', regex=True)]
    inland = shapely.make_valid(water.to_crs(CRS).union_all())

    lines = pyogrio.read_dataframe(OSM, layer="lines", columns=["other_tags"])
    coast = lines[lines.other_tags.fillna("").str.contains('"natural"=>"coastline"')].to_crs(CRS)
    faces = shapely.polygonize(list(shapely.get_parts(shapely.union_all([*coast.geometry, area.boundary]))))
    seeds = [Point(*TO_CRS.transform(lon, lat)) for lon, lat in SEA_SEEDS]
    sea = [f for f in shapely.get_parts(faces) if area.contains(f.representative_point()) and any(f.contains(s) for s in seeds)]
    print("sea faces", len(sea), "area km²", round(sum(f.area for f in sea) / 1e6, 1))

    water_all = shapely.union_all([inland, *sea]).intersection(area).buffer(0.5).buffer(-0.5).simplify(1.5)
    water_polys = [p for p in polygons(water_all) if p.area > 50]
    land = area.difference(shapely.MultiPolygon(water_polys)).simplify(1.5)
    land_polys = [p for p in polygons(land) if p.area > 50]
    (OUT / "water.bin").write_bytes(pack(water_polys))
    (OUT / "land.bin").write_bytes(pack(land_polys))
    print(f"water {len(water_polys)} polys {sum(p.area for p in water_polys)/1e6:.1f} km²; land {len(land_polys)};",
          f"{(OUT/'water.bin').stat().st_size/1e6:.2f} + {(OUT/'land.bin').stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
