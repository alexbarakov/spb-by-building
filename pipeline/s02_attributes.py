"""Years, floors and heights per building.

Year sources, in order of trust (date_flag in brackets):
  monument   Wikidata item of a cultural heritage object (EGROKN id) inside the footprint or within 20 m:
             to the year [3], or spread across its decade or century [4]
  hoith      "How old is this house" (Kon-Tiki maps, ODbL, Nov 2023): official address plan, housing passports,
             citywalls and OSM merged; the first year of its range [0], or spread across the range [1]
  osm        OSM start_date: a year [0]; a range or a century is spread across it [1]
  mkd        GIS ZhKKh apartment-building registry (tochno.st dump, Sept 2026, CC BY 4.0), geocoded to the house,
             within the footprint or 15 m [0]; its 1917 means "before the revolution" and is spread across 1880–1917 [1]
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
    g = pd.read_parquet("data/raw/gisgkh_spb.parquet")
    g = g[g.qc_geo.isin(["Точные координаты", "Ближайший дом"])]
    year = pd.to_numeric(g.building_year, errors="coerce").fillna(pd.to_numeric(g.comissioning_year, errors="coerce"))
    g = g.assign(year=year)[year.between(1700, 2026)]
    x, y = TO_CRS.transform(g.longitude.astype(float).values, g.latitude.astype(float).values)
    pts = gpd.GeoDataFrame({"year": g.year.astype(int).values, "series": g.plan_series.values},
                           geometry=gpd.points_from_xy(x, y), crs=CRS)
    j = attach_points(b, pts, 15)
    return j.drop_duplicates("identificatie").set_index("identificatie")


def hoith_dates(b):
    """Kon-Tiki footprints matched to OSM buildings by a point inside each footprint."""
    h = gpd.read_parquet("data/raw/hoith_spb.parquet", columns=["r_years_str", "r_year_int", "r_architect", "r_style", "r_cw_url", "geometry"])
    h = h[pd.to_numeric(h.r_year_int, errors="coerce") > 0].copy()
    yrs = h.r_years_str.fillna("").str.findall(r"(?<!\d)(1[7-9]\d\d|20[0-2]\d)(?!\d)")
    h["lo"] = yrs.map(lambda v: int(v[0]) if v else None)
    rng = h.r_years_str.fillna("").str.extract(r"(1[7-9]\d\d|20[0-2]\d)\s*[-–]\s*(1[7-9]\d\d|20[0-2]\d)")
    h["hi"] = pd.to_numeric(rng[1], errors="coerce")
    h["lo"] = h.lo.fillna(pd.to_numeric(h.r_year_int, errors="coerce"))
    pts = gpd.GeoDataFrame(h.drop(columns="geometry"), geometry=h.geometry.representative_point(), crs=CRS)
    j = gpd.sjoin(pts, b[["identificatie", "geometry"]], predicate="within").drop(columns="index_right")
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
    b["series"] = b.identificatie.map(r.series)

    hoith = None  # filled below, after OSM

    for i, s in enumerate(b.start_date.values):
        d = parse_osm_date(s)
        if d and 1700 <= d[0] <= 2025:
            lo, hi = d[0], min(d[1], 2025)
            year[i] = lo if lo == hi else int(lo + unit(ids[i], "osm") * (hi - lo))
            flag[i] = EXACT if lo == hi else FAINT
            src[i] = "osm"

    # Kon-Tiki over OSM; over the registry only where the registry has its "before 1917" placeholder.
    h = hoith_dates(b)
    for i in np.where(b.identificatie.isin(h.index))[0]:
        if src[i] == "mkd" and flag[i] == EXACT:
            continue
        lo, hi = int(h.at[ids[i], "lo"]), h.at[ids[i], "hi"]
        if pd.notna(hi) and hi > lo:
            year[i], flag[i] = int(lo + unit(ids[i], "hoith") * (hi - lo)), FAINT
        else:
            year[i], flag[i] = lo, EXACT
        src[i] = "hoith"
    b["architect_hoith"] = b.identificatie.map(h.r_architect).replace("", None)
    b["style_hoith"] = b.identificatie.map(h.r_style).replace("", None)
    b["citywalls"] = b.identificatie.map(h.r_cw_url).replace("", None)

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
