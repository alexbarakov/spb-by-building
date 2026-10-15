"""Граф онтологии (web/data/graph.json): люди, события и организации, связанные со зданиями проверенными текстами.

Тексты — заметки слоёв из web/data/layers.json (TEXT_LAYERS). Связь хранит текст и источник. Здания одного названия
сливаются в одно место; у места есть координаты, чтобы карта могла к нему подлететь.
"""
import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .city import ORIGIN
from .ontology import ENTITIES
from .s03_tiles import osm_number

def key_of(ident):
    """The id the viewer looks buildings up by: the osm number as JavaScript prints it (no .0)."""
    return str(int(osm_number(ident)))


TEXT_LAYERS = ["pushkin", "dostoevsky", "silver", "people", "revolution", "blockade", "eggs", "paradnye", "bars",
               "owners"]


def main():
    layers = {L["id"]: L for L in json.load(open("web/data/layers.json"))}
    b = gpd.read_parquet("data/buildings.parquet", columns=["identificatie", "year", "name", "addr:street",
                                                              "addr:housenumber", "geometry"])
    b["key"] = [key_of(i) for i in b.identificatie]
    c = b.geometry.centroid
    where = {k: (round(x - ORIGIN[0], 1), round(-(y - ORIGIN[1]), 1), int(yr) if yr == yr else None)
             for k, x, y, yr in zip(b.key, c.x, c.y, b.year)}
    addr = {k: (n if isinstance(n, str) else None) or (f"{s}, {h}" if isinstance(s, str) and isinstance(h, str) else None)
            for k, n, s, h in zip(b.key, b.name, b["addr:street"], b["addr:housenumber"])}

    texts = []  # (key, name, text, source, layer title)
    for lid in TEXT_LAYERS:
        L = layers.get(lid)
        for key, n in (L or {}).get("notes", {}).items():
            if isinstance(n, dict) and n.get("story") and key in where:
                # A building with several plaques has them joined by " · "; each plaque is its own text, so a name
                # and a year from two different plaques never make a link.
                for part in n["story"].split(" · "):
                    texts.append((key, n.get("name"), part.strip(), n.get("source"), L["title"]))

    nodes, links = [], []
    for eid, kind, label, years, pattern in ENTITIES:
        rx, seen = re.compile(pattern), set()
        for key, name, story, source, origin in texts:
            if rx.search(story) and (key, story) not in seen:
                seen.add((key, story))
                links.append(dict(e=eid, bag=key, text=story, source=source, via=origin))
        if seen:
            nodes.append(dict(id=eid, type=kind, label=label, years=years))
        else:
            print("нет зданий для", eid)

    names = {}
    for key, name, *_ in texts:
        if name and key not in names:
            names[key] = name
    wiki = json.load(open("web/data/wiki.json"))
    wk = pd.read_parquet("data/wiki_index.parquet")
    wk = dict(zip(wk.identificatie.map(key_of), wk.wk))
    places, place_of = {}, {}
    for key in sorted({l["bag"] for l in links}):
        w = wiki[wk[key]] if key in wk and 0 <= wk[key] < len(wiki) else {}
        name = names.get(key) or (w.get("label") if isinstance(w, dict) else None) or addr.get(key)
        # A building with no name or address in OSM keeps its own place, under a plain label.
        pid = "p:" + re.sub(r"[^\w]+", "-", name.lower()).strip("-") if name else "p:" + key
        name = name or "Здание без адреса"
        name = name if len(name) <= 70 else name[:68].rsplit(" ", 1)[0] + "…"
        p = places.setdefault(pid, dict(name=name, bags=[], year=9999, photo=None, _xz=[]))
        x, z, year = where[key]
        p["bags"].append(key)
        p["_xz"].append((x, z))
        if year:
            p["year"] = min(p["year"], year)
        img = w.get("image") if isinstance(w, dict) else None
        p["photo"] = p["photo"] or (img.get("thumb") if isinstance(img, dict) else None)
        place_of[key] = pid
    for p in places.values():
        xz = p.pop("_xz")
        p["x"], p["z"] = round(sum(a for a, _ in xz) / len(xz), 1), round(sum(b for _, b in xz) / len(xz), 1)
        if p["year"] == 9999:
            p["year"] = ""
    merged = {}
    for l in links:
        k = (l["e"], place_of[l["bag"]])
        m = merged.setdefault(k, dict(e=l["e"], p=k[1], texts=[]))
        t = dict(text=l["text"], source=l["source"], via=l["via"])
        if t not in m["texts"]:
            m["texts"].append(t)
    links = list(merged.values())
    Path("web/data/graph.json").write_text(json.dumps(dict(nodes=nodes, places=places, links=links),
                                                      ensure_ascii=False, separators=(",", ":")))
    deg = {}
    for l in links:
        deg.setdefault(l["e"], set()).add(l["p"])
    print(len(nodes), "сущностей,", len(places), "мест,", len(links), "связей")
    print(sorted(((len(v), k) for k, v in deg.items()), reverse=True)[:15])


if __name__ == "__main__":
    main()
