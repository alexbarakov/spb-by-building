"""Pack buildings into 600 m binary tiles + a city config JSON.

Local frame: metres from the city origin (city.ORIGIN), x east, z south (three.js, y up).
Tile layout (little-endian, every section 4-byte aligned):
  header  u32 magic, nB, nP, nR, nV; f32 originX, originZ
  B       u32 gid[nB]; i16 year[nB]; u8 flag[nB]; u8 period[nB]; u8 floors[nB];
          u32 lay0[nB]; u32 lay1[nB] (layer bits, see s05_layers); u32 partStart[nB+1]
  P       f32 height[nP]; u32 ringStart[nP+1]
  R       u32 vertStart[nR+1]; u8 hole[nR]
  V       i16 xz[2*nV], decimetres from the tile origin
"""
import json
import struct
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from . import city
from .periods import PERIODS, UNKNOWN

DAM = city.ORIGIN
TILE = 600.0
SIMPLIFY = 0.25
OUT = Path("web/data")
MAGIC = 0x32424241  # 'ABB2'


def pad4(b: bytes) -> bytes:
    return b + b"\0" * (-len(b) % 4)


def to_local(coords: np.ndarray) -> np.ndarray:
    return np.c_[coords[:, 0] - DAM[0], -(coords[:, 1] - DAM[1])]


def rings_of(geom):
    polys = getattr(geom, "geoms", [geom])
    for poly in polys:
        if poly.is_empty:
            continue
        yield shapely.get_coordinates(poly.exterior)[:-1], 0
        for hole in poly.interiors:
            yield shapely.get_coordinates(hole)[:-1], 1


def pack_tile(origin, rows):
    gid, year, flag, period, floors, lay0, lay1, part_start = [], [], [], [], [], [], [], [0]
    heights, ring_start, vert_start, holes, verts = [], [0], [0], [], []
    for b in rows:
        gid.append(b["gid"]); year.append(b["year"]); flag.append(b["flag"])
        period.append(b["period"]); floors.append(b["floors"])
        lay0.append(b["lay0"]); lay1.append(b["lay1"])
        for h, geom in b["parts"]:
            heights.append(h)
            for ring, hole in rings_of(geom):
                if len(ring) < 3:
                    continue
                loc = (to_local(ring) - origin) * 10
                verts.append(np.round(loc).astype(np.int16))
                holes.append(hole)
                vert_start.append(vert_start[-1] + len(ring))
            ring_start.append(len(holes))
        part_start.append(len(heights))
    nB, nP, nR = len(gid), len(heights), len(holes)
    V = np.concatenate(verts) if verts else np.zeros((0, 2), np.int16)
    out = struct.pack("<5I2f", MAGIC, nB, nP, nR, len(V), *origin)
    out += pad4(np.array(gid, "<u4").tobytes())
    out += pad4(np.array(year, "<i2").tobytes())
    out += pad4(np.array(flag, "u1").tobytes())
    out += pad4(np.array(period, "u1").tobytes())
    out += pad4(np.array(floors, "u1").tobytes())
    out += np.array(lay0, "<u4").tobytes() + np.array(lay1, "<u4").tobytes()
    out += pad4(np.array(part_start, "<u4").tobytes())
    out += pad4(np.array(heights, "<f4").tobytes())
    out += pad4(np.array(ring_start, "<u4").tobytes())
    out += pad4(np.array(vert_start, "<u4").tobytes())
    out += pad4(np.array(holes, "u1").tobytes())
    out += pad4(V.astype("<i2").tobytes())
    return out


def osm_number(ident: str) -> float:
    """Ways as positive numbers, relations as negative, so one float64 holds either."""
    return float(ident[1:]) * (1 if ident[0] == "w" else -1)


def main():
    b = gpd.read_parquet("data/buildings.parquet")
    b = b.merge(pd.read_parquet("data/layers.parquet"), on="identificatie", how="left")
    b[["lay0", "lay1"]] = b[["lay0", "lay1"]].fillna(0).astype(np.uint32)
    gid = {k: i for i, k in enumerate(b.identificatie)}
    geoms = shapely.simplify(b.geometry.values, SIMPLIFY, preserve_topology=True)
    parts = {k: [(float(h), g)] for k, h, g in zip(b.identificatie, b.height, geoms)}

    c = to_local(np.c_[b.geometry.centroid.x, b.geometry.centroid.y])
    b["tx"] = np.floor(c[:, 0] / TILE).astype(int)
    b["tz"] = np.floor(c[:, 1] / TILE).astype(int)

    (OUT / "tiles").mkdir(parents=True, exist_ok=True)
    index = []
    for (tx, tz), grp in b.groupby(["tx", "tz"]):
        origin = np.array([tx * TILE, tz * TILE])
        rows = [dict(gid=gid[r.identificatie], year=int(r.year), flag=int(r.date_flag),
                     period=int(r.period), floors=int(r.floors),
                     lay0=int(r.lay0), lay1=int(r.lay1), parts=parts[r.identificatie])
                for r in grp.itertuples()]
        data = pack_tile(origin, rows)
        name = f"{tx}_{tz}.bin"
        (OUT / "tiles" / name).write_bytes(data)
        cx, cz = origin + TILE / 2
        index.append(dict(file=name, tx=int(tx), tz=int(tz), n=len(rows), bytes=len(data),
                          dist=round(float(np.hypot(cx, cz)))))
    index.sort(key=lambda t: t["dist"])

    # Bundle tiles into a few packs, nearest the origin first, so the city loads centre-out in few requests.
    packs, n_packs = [], 8
    per = -(-len(index) // n_packs)
    for k in range(n_packs):
        chunk = index[k * per:(k + 1) * per]
        if not chunk:
            break
        name, offset, blob = f"pack{k}.bin", 0, bytearray()
        for t in chunk:
            data = (OUT / "tiles" / t["file"]).read_bytes()
            t.update(pack=name, offset=offset, length=len(data))
            blob += data; offset += len(data)
        (OUT / name).write_bytes(blob)
        packs.append(name)

    # Per-building lookup for the card: OSM id, height (dm), floors source, date flag, Wikidata Q-number.
    attrs = np.zeros(len(b), dtype=[("osm", "<f8"), ("h", "<u2"), ("fsrc", "u1"), ("flag", "u1"), ("year", "<i2"),
                                    ("src", "<i2"), ("q", "<u4"), ("lay0", "<u4"), ("lay1", "<u4"), ("wk", "<i4")])
    attrs["osm"] = [osm_number(i) for i in b.identificatie]
    attrs["h"] = np.round(b.height.fillna(0) * 10).clip(0, 65535)
    attrs["fsrc"] = b.floors_src; attrs["flag"] = b.date_flag; attrs["year"] = b.year
    attrs["src"] = b.year_src.map({"": 0, "mkd": 1, "osm": 2, "monument": 3, "hoith": 4}).fillna(0).astype(int)
    attrs["q"] = pd.to_numeric(b.wikidata_item.astype(str).str.extract(r"Q(\d+)")[0], errors="coerce").fillna(0).astype(int)
    attrs["lay0"] = b.lay0; attrs["lay1"] = b.lay1
    wk_path = Path("data/wiki_index.parquet")
    wk = pd.read_parquet(wk_path).set_index("identificatie").wk if wk_path.exists() else pd.Series(dtype=int)
    attrs["wk"] = b.identificatie.map(wk).fillna(-1).astype(int)
    (OUT / "attrs.bin").write_bytes(attrs.tobytes())

    # Architect, style and the citywalls page from the Kon-Tiki dataset, by building index; read lazily by the card.
    extras = {}
    for i, (a, st, cw, wa, wn, wp, wy) in enumerate(zip(b.get("architect_hoith"), b.get("style_hoith"), b.get("citywalls"),
                                                     b.get("wv_author"), b.get("wv_name"), b.get("wv_page"), b.get("wv_year"))):
        # The heritage register's author and dating win over Kon-Tiki's.
        a = wa if isinstance(wa, str) and wa.strip() else a
        e = {k: v for k, v in (("a", a), ("s", st), ("cw", cw), ("n", wn), ("wv", wp), ("y", wy)) if isinstance(v, str) and v.strip()}
        if "cw" in e:
            e["cw"] = e["cw"].rsplit("house", 1)[-1].split(".")[0]
        if e:
            extras[i] = e
    (OUT / "extras.json").write_text(json.dumps(extras, ensure_ascii=False, separators=(",", ":")))

    known = b[b.date_flag != 5]
    hist = {}
    for p, y in zip(known.period, known.year):
        hist.setdefault(int(y), [0] * len(PERIODS))[p] += 1
    config = dict(
        city=city.NAME, label=city.LABEL, tileSize=TILE, origin=DAM,
        home=dict(x=-600, z=-300, azimuth=15, elevation=40, span=7500),
        periods=[dict(key=k, label=l, from_=a, to=bb, color=col) for k, l, a, bb, col in PERIODS],
        unknown=dict(label=UNKNOWN[1], color=UNKNOWN[4], count=int((b.date_flag == 5).sum())),
        yearMin=int(known.year.min()), yearMax=2025,
        histogram={str(k): v for k, v in sorted(hist.items())},
        attrStride=attrs.dtype.itemsize,
        tiles=index,
        packs=packs,
        stats=dict(buildings=len(b), dated=int(len(known)), unknown=int((b.date_flag == 5).sum()),
                   bySource={k: int(v) for k, v in known.year_src.value_counts().items()},
                   floorsTagged=int((b.floors_src == 0).sum()), floorsHeight=int((b.floors_src == 1).sum()),
                   floorsDefault=int((b.floors_src == 2).sum())),
    )
    (OUT / "city.json").write_text(json.dumps(config, ensure_ascii=False, separators=(",", ":")).replace('"from_"', '"from"'))
    total = sum(t["bytes"] for t in index)
    print(f"{len(index)} tiles, {total/1e6:.1f} MB, attrs {attrs.nbytes/1e6:.1f} MB")


if __name__ == "__main__":
    main()
