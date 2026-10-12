"""Years, floors and heights per building.

Year sources, in order of trust (date_flag in brackets):
  monument   Wikidata item of a cultural heritage object (EGROKN id) inside the footprint or within 20 m:
             to the year [3], or spread across its decade or century [4]
  osm        OSM start_date: a year [0]; a range or a century is spread across it [1]
  mkd        apartment-building registry (Reforma ZhKKh, 2016 snapshot) within the footprint or 15 m [0];
             its 1917 means "before the revolution" and is spread across 1880–1917 [1]
  unknown    no source, or a year before 1700, which in Petersburg is a tagging error [5]: drawn grey,
             and only once the timeline reaches today
Floors: OSM building:levels [0], else height / 3.2 m [1], else a default for the building type [2].
"""
import hashlib
import re

import geopandas as gpd
import numpy as np
import pandas as pd

from .city import CRS, TO_CRS
from .periods import PERIODS, period_index

EXACT, FAINT, MONUMENT, MONUMENT_APPROX, UNKNOWN = 0, 1, 3, 4, 5
STOREY_M = 3.2
DEFAULT_LEVELS = {"apartments": 5, "residential": 5, "house": 2, "detached": 2, "garages": 1, "garage": 1,
                  "service": 1, "shed": 1, "industrial": 2, "warehouse": 2, "retail": 2, "commercial": 3,
                  "office": 5, "school": 3, "church": 3, "cathedral": 6}


def unit(key: str, salt: str) -> float:
    return int(hashlib.md5((salt + key).encode()).hexdigest()[:8], 16) / 2**32


def parse_osm_date(s):
    """(lo, hi) from an OSM start_date: 1883, 1764..1788, 1704-04-04, 01.09.2025, C18, ~1900, 1900s."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip()
    if m := re.fullmatch(r"C(\d{1,2})", s):
        c = int(m.group(1)); return (c - 1) * 100, c * 100 - 1
    if m := re.fullmatch(r"(\d{4})s", s):
        y = int(m.group(1)); return y, y + 9
    years = [int(y) for y in re.findall(r"(?<!\d)(1[0-9]{3}|20[0-2][0-9])(?!\d)", s)]
    if not years:
        return None
    return (min(years), max(years)) if ".." in s or "-" in s[4:5] and len(years) > 1 else (years[0], years[0])


def attach_points(b: gpd.GeoDataFrame, pts: gpd.GeoDataFrame, radius: float) -> pd.DataFrame:
    """Each point to the building that contains it, else the nearest within `radius`."""
    inside = gpd.sjoin(pts, b[["identificatie", "geometry"]], predicate="within")
    rest = pts[~pts.index.isin(inside.index)]
    near = gpd.sjoin_nearest(rest, b[["identificatie", "geometry"]], max_distance=radius)
    return pd.concat([inside, near]).drop(columns="index_right")


def wikidata_dates(b):
    w = pd.read_csv("data/raw/wd_spb.csv")
    w = w[w.t.notna() & w.okn.notna()].copy()
    w["year"] = w.t.str.extract(r"^\+?(\d{4})")[0].astype(float)
    w = w[w.year.between(1700, 2025)].drop_duplicates("i")
    ll = w.coord.str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
    x, y = TO_CRS.transform(ll[0].values, ll[1].values)
    pts = gpd.GeoDataFrame(w[["i", "year", "prec"]], geometry=gpd.points_from_xy(x, y), crs=CRS)
    j = attach_points(b, pts, 20)
    # One heritage date per building: the earliest, as for Paris and Amsterdam.
    return j.sort_values("year").drop_duplicates("identificatie").set_index("identificatie")


def registry_dates(b):
    k = pd.read_csv("data/raw/kuk_reformagkh.csv", usecols=["latitude", "longitude", "year"])
    k = k[k.year.notna() & k.latitude.between(59.7, 60.2) & k.longitude.between(29.6, 30.8)]
    x, y = TO_CRS.transform(k.longitude.values, k.latitude.values)
    pts = gpd.GeoDataFrame({"year": k.year.astype(int).values}, geometry=gpd.points_from_xy(x, y), crs=CRS)
    j = attach_points(b, pts, 15)
    return j.drop_duplicates("identificatie").set_index("identificatie")


def main():
    b = gpd.read_parquet("data/osm_buildings.parquet").reset_index(drop=True)
    n = len(b)
    year = np.full(n, -1); flag = np.full(n, UNKNOWN); src = np.array([""] * n, dtype=object)
    ids = b.identificatie.values

    # mkd registry, lowest trust first, so later sources overwrite it
    r = registry_dates(b)
    for i in np.where(b.identificatie.isin(r.index))[0]:
        y = int(r.at[ids[i], "year"])
        if y == 1917:
            year[i], flag[i] = 1880 + int(unit(ids[i], "1917") * 37), FAINT
        else:
            year[i], flag[i] = y, EXACT
        src[i] = "mkd"

    for i, s in enumerate(b.start_date.values):
        d = parse_osm_date(s)
        if d and 1700 <= d[0] <= 2025:
            lo, hi = d[0], min(d[1], 2025)
            year[i] = lo if lo == hi else int(lo + unit(ids[i], "osm") * (hi - lo))
            flag[i] = EXACT if lo == hi else FAINT
            src[i] = "osm"

    w = wikidata_dates(b)
    for i in np.where(b.identificatie.isin(w.index))[0]:
        y, prec = int(w.at[ids[i], "year"]), w.at[ids[i], "prec"]
        span = 0 if prec >= 9 else 9 if prec == 8 else 99
        year[i] = y + int(unit(ids[i], "wd") * span) if span else y
        flag[i] = MONUMENT if span == 0 else MONUMENT_APPROX
        src[i] = "monument"
    b["wikidata_item"] = b.identificatie.map(w.i)

    unknown = flag == UNKNOWN
    year[unknown] = 2025
    b["year"] = year; b["date_flag"] = flag.astype(np.uint8); b["year_src"] = src
    b["period"] = np.where(unknown, len(PERIODS), [period_index(y) for y in year]).astype(np.uint8)

    levels = pd.to_numeric(b["building:levels"].str.extract(r"(\d+)")[0], errors="coerce")
    height = pd.to_numeric(b["height"].str.extract(r"([\d.]+)")[0], errors="coerce")
    default = b.building.map(DEFAULT_LEVELS).fillna(3)
    b["floors"] = levels.fillna(np.round(height / STOREY_M)).fillna(default).clip(1, 99).astype(np.uint8)
    b["floors_src"] = np.where(levels.notna(), 0, np.where(height.notna(), 1, 2)).astype(np.uint8)
    b["height"] = height.fillna(b.floors * STOREY_M + 1.0).clip(2.5, 400)

    b.to_parquet("data/buildings.parquet")
    print(f"{n} buildings; dated {(~unknown).sum()} ({(~unknown).mean():.1%}):",
          pd.Series(src[~unknown]).value_counts().to_dict(), "| flags", pd.Series(flag).value_counts().to_dict())
    print("floors from", pd.Series(b.floors_src).value_counts().to_dict())


if __name__ == "__main__":
    main()
