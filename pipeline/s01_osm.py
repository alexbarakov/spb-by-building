"""Buildings from OpenStreetMap (BBBike extract, ODbL): footprint, levels, height, OSM's own dates and names."""
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from .city import CRS, OSM

TAGS = ["building:levels", "height", "start_date", "wikidata", "building:architecture", "architect",
        "addr:street", "addr:housenumber", "building:min_level", "min_height", "amenity", "religion", "denomination"]
DROP_TYPES = {"roof", "construction", "ruins", "no"}


def tag_frame(other: pd.Series) -> pd.DataFrame:
    s = other.fillna("").astype(str)
    return pd.DataFrame({k: s.str.extract(r'"%s"=>"([^"]*)"' % re.escape(k))[0] for k in TAGS})


def main():
    df = pyogrio.read_dataframe(OSM, layer="multipolygons", columns=["osm_id", "osm_way_id", "building", "name", "other_tags"],
                                where="building IS NOT NULL")
    df = df[~df.building.isin(DROP_TYPES)]
    df = pd.concat([df.drop(columns="other_tags"), tag_frame(df.other_tags)], axis=1)
    df["identificatie"] = np.where(df.osm_way_id.notna(), "w" + df.osm_way_id.astype(str), "r" + df.osm_id.astype(str))
    g = gpd.GeoDataFrame(df, geometry="geometry", crs=4326).to_crs(CRS)
    g = g[g.geometry.area > 12].drop_duplicates("identificatie")
    g.to_parquet("data/osm_buildings.parquet")
    print(len(g), "buildings;", g.building.value_counts().head(8).to_dict())


if __name__ == "__main__":
    main()
