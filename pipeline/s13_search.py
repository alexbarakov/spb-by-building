"""Поиск по адресу, улице и названию (web/data/search.json и web/data/search/<k>.json).

search.json грузится при первом нажатии на лупу и держит то, что нужно для подсказок:
  streets: [название, номер шарда, число зданий, x, z, район] — улица из OSM addr:street и адресного плана Кон-Тики.
    Одноимённые улицы разных районов (Московская в Пушкине и в Колпине) — разные записи.
  names: [название, вид, x, z, где, gid, gid…] (где — дом человека или архитектора) — здания Wikidata, Википутеводителя и OSM, места слоёв, люди графа.
  kinds, districts: подписи к видам и районам по их номерам.
search/<k>.json — номера домов улиц одного шарда (по первой букве названия): {улица: [[номер, gid, x, z], …]}.
gid — номер здания в data/buildings.parquet, как в тайлах. Координаты — локальные метры (x на восток, z на юг).
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .city import ORIGIN
from .layers import districts
from .s03_tiles import osm_number

OUT = Path("web/data")
GAP = 700          # м: здания одной улицы дальше 2·GAP друг от друга — разные улицы, если они и в разных районах
GENERIC_RE = re.compile(r"^(жил\w* (дом|здание|корпус)|здание$|дом$|флигел|корпус|гараж|склад|трансформатор|тп\b|котельная|"
                        r"сарай|навес|гостиница$|конторское здание$|билетная касса$|дача$|особняк$|церковь$|часовня$|"
                        r"школа$|детский сад$|казармы$|служебн|хозяйственн|производственн\w* (здание|корпус)$)")
TRADE = {"retail", "kiosk", "service", "store", "commercial", "industrial", "warehouse", "garage", "garages", "supermarket"}
GENERIC = 3        # название, которое носят столько зданий и больше, — тип здания, а не имя

# Сокращения типов улиц; то же в web/app.js (STREET_TYPES).
TYPES = {"улица": "улица", "ул": "улица", "проспект": "проспект", "пр": "проспект", "пр-т": "проспект",
         "пр-кт": "проспект", "просп": "проспект", "набережная": "набережная", "наб": "набережная",
         "переулок": "переулок", "пер": "переулок", "площадь": "площадь", "пл": "площадь", "бульвар": "бульвар",
         "б-р": "бульвар", "бул": "бульвар", "шоссе": "шоссе", "ш": "шоссе", "проезд": "проезд", "пр-д": "проезд",
         "линия": "линия", "линии": "линия", "лин": "линия", "аллея": "аллея", "дорога": "дорога", "дор": "дорога",
         "тупик": "тупик", "туп": "тупик", "мост": "мост", "спуск": "спуск", "сквер": "сквер", "сад": "сад"}
FILLER = {"реки", "р", "река", "канала", "кан", "канал", "острова", "о", "о-в"}


def normal(s: str) -> str:
    s = str(s).lower().replace("ё", "е").replace("–", "-").replace("—", "-")
    s = re.sub(r"в\.\s*о\.?", " во ", s)
    s = re.sub(r"п\.\s*с\.?", " пс ", s)
    s = s.replace("васильевского острова", "во").replace("петроградской стороны", "пс")
    s = re.sub(r"[^a-zа-я0-9/-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def street_key(name: str) -> str:
    """Одна и та же улица в OSM и у Кон-Тики: тип полным словом, порядок слов не важен."""
    toks = [TYPES.get(t, t) for t in normal(name).split() if t not in FILLER]
    return " ".join(sorted(toks))


NUM = re.compile(r"^(\d+(?:-\d+)*)\s*([а-я](?![а-я]))?\s*(?:/\s*(\d+\s*[а-я]?))?(.*)$")


def house_label(raw: str) -> str | None:
    """'12 к2 литА', '25а к1 литБ', '12/14', '114-116': номер, корпус, строение и литера в одном виде."""
    s = raw.lower().replace("–", "-").replace("—", "-").strip()
    m = NUM.match(s)
    if not m:
        return None
    base, letter, slash, rest = m.groups()
    out = base + (letter or "") + (f"/{slash.replace(' ', '')}" if slash else "")
    k = re.search(r"(?:к|корп|корпус)\.?\s*(\d+)", rest)
    st = re.search(r"(?:с|стр|строение)\.?\s*(\d+)", rest)
    lit = re.search(r"(?:лит|литера|литер)\.?\s*([а-я]+\d*)", rest)
    if k: out += f" к{k[1]}"
    if st: out += f" с{st[1]}"
    if lit: out += f" лит{lit[1].upper()}"
    return out


def hoith_address(a: str):
    """'191186, г.Санкт-Петербург, Невский проспект, дом 28, литера А' -> ('Невский проспект', '28 литА')."""
    parts = [p.strip() for p in str(a).split(",")]
    for i, p in enumerate(parts):
        m = re.match(r"^дом\s+(.+)$", p)
        if m and i > 0:
            street = parts[i - 1]
            if re.match(r"^(г\.|город|посёлок|поселок|пос\.|деревня|садоводство|\d{6})", street, re.I):
                return None
            num = m[1] + " " + " ".join(parts[i + 1:])
            num = num.replace("корпус", "к").replace("литера", "лит").replace("строение", "с")
            lab = house_label(num)
            return (street, lab) if lab else None
    return None


def main():
    b = gpd.read_parquet("data/buildings.parquet", columns=["identificatie", "name", "building", "addr:street",
                                                              "addr:housenumber", "wv_name", "geometry"])
    n = len(b)
    cent = b.geometry.centroid
    X = np.round(cent.x.values - ORIGIN[0]).astype(int)
    Z = np.round(-(cent.y.values - ORIGIN[1])).astype(int)
    gid_of_osm = {str(int(osm_number(i))): g for g, i in enumerate(b.identificatie)}
    gid_of_ident = {i: g for g, i in enumerate(b.identificatie)}

    # ---- addresses: OSM first, then Kon-Tiki's address plan for what OSM lacks or adds (corner houses) ----
    addr = []  # (street as written, label, gid)
    for g, (s, h) in enumerate(zip(b["addr:street"], b["addr:housenumber"])):
        if isinstance(s, str) and isinstance(h, str):
            for part in re.split(r"[;,]", h):
                lab = house_label(part)
                if lab:
                    addr.append((s.strip(), lab, g, "osm"))
    h = gpd.read_parquet("data/raw/hoith_spb.parquet", columns=["r_adress", "geometry"])
    h = h[h.r_adress.fillna("").str.contains("дом ")]
    pts = gpd.GeoDataFrame({"a": h.r_adress.values}, geometry=h.geometry.representative_point().values, crs=h.crs)
    j = gpd.sjoin(pts, gpd.GeoDataFrame(geometry=b.geometry.values, crs=b.crs), predicate="within")
    n_hoith = 0
    for a, g in zip(j.a, j.index_right):
        p = hoith_address(a)
        if p:
            addr.append((p[0], p[1], int(g), "hoith")); n_hoith += 1

    # one display name per street: OSM's spelling where OSM has the street
    spell = defaultdict(Counter)
    for s, _, _, src in addr:
        spell[street_key(s)][s] += 10 if src == "osm" else 1
    D = districts()
    dnames = [re.sub(r"\s+район$", " район", d) for d in D.name]
    dist_idx = gpd.sjoin(gpd.GeoDataFrame(geometry=cent.values, crs=b.crs), D, predicate="within")
    dist_of = np.full(n, -1)
    dist_of[dist_idx.index.values] = dist_idx.index_right.values
    # Kronstadt, Zelenogorsk, Lomonosov lie outside the districts' extract: the nearest district
    out = np.where(dist_of < 0)[0]
    near = gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=cent.values[out], crs=b.crs), D, max_distance=30000)
    near = near[~near.index.duplicated()]
    dist_of[out[near.index.values]] = near.index_right.values

    by_key = defaultdict(dict)  # key -> {label: [gids]}
    for s, lab, g, _ in addr:
        gs = by_key[street_key(s)].setdefault(lab, [])
        if g not in gs:
            gs.append(g)

    streets, shards = [], defaultdict(dict)
    for key, nums in by_key.items():
        name = spell[key].most_common(1)[0][0]
        gids = sorted({g for gs in nums.values() for g in gs})
        # split far-apart groups that lie in different districts: namesakes in Pushkin, Kolpino, Kronstadt…
        geoms = shapely.buffer(shapely.points(np.c_[X[gids], Z[gids]]), GAP)
        groups = shapely.get_parts(shapely.union_all(geoms))
        tree = shapely.STRtree(groups)
        grp_of = {g: int(tree.query(shapely.Point(X[g], Z[g]), predicate="intersects")[0]) for g in gids}
        dist_of_grp = {}
        for k in range(len(groups)):
            ds = Counter(int(dist_of[g]) for g in gids if grp_of[g] == k)
            dist_of_grp[k] = ds.most_common(1)[0][0]
        clusters = defaultdict(list)  # district -> gids
        for g in gids:
            clusters[dist_of_grp[grp_of[g]]].append(g)
        for d, cg in clusters.items():
            cs = set(cg)
            entries = []
            for lab, gs in nums.items():
                for g in gs:
                    if g in cs:
                        entries.append([lab, int(g), int(X[g]), int(Z[g])])
            def order(e):
                m = re.match(r"\d+", e[0])
                return (int(m[0]) if m else 0, e[0])
            entries.sort(key=order)
            first = next((t for t in normal(name).split() if re.match(r"[а-яa-z]", t) and t not in TYPES and t not in FILLER),
                         normal(name)[:1] or "_")
            shard = "абвгдежзиклмнопрстуфхцчшщэюя".find(first[0]) + 1  # 0: digits and Latin
            sname = name if len(clusters) == 1 else f"{name}\t{d}"
            shards[shard][sname] = entries
            xs, zs = X[cg], Z[cg]
            streets.append([name, shard, len(cs), int((xs.min() + xs.max()) / 2), int((zs.min() + zs.max()) / 2), int(d),
                            *([1] if len(clusters) > 1 else [])])
    streets.sort(key=lambda s: (s[0], -s[2]))
    street_keys = {street_key(s[0]) for s in streets}

    # ---- names ----
    kinds = ["Здание", "Жил или работал здесь", "Архитектор"]
    names, seen = [], set()
    wiki = json.load(open(OUT / "wiki.json"))
    # a name that many buildings carry is a type of building ('Жилой дом', 'Флигель', a chain of shops)
    common = Counter(lab for lab, _ in {(str(x).strip().lower(), g) for col in ("wv_name", "name") for g, x in b[col].dropna().items()})

    def is_address(label):
        m = re.match(r"^(.*?[а-яa-z].*?)[\s,]+(?:д\s+|дом\s+)?\d+\S*(?:\s+(?:к|корп|лит|литера|стр|с)\s*\S+)*$", normal(label))
        return bool(m) and street_key(m[1]) in street_keys

    def add(label, kind, gids, where=""):
        label = re.sub(r"\s+", " ", str(label)).strip(" .")
        label = re.sub(r",\s*(г\.\s*)?Санкт-Петербург$", "", label)
        # 'Исаакиевская площадь 9, Дом Мятлевых': the address is found as one; the name is what follows it
        m = re.match(r"^(.*?\d+\S*),\s*(.+)$", label)
        if m and is_address(m[1]):
            label = m[2]
        gids = [g for g in dict.fromkeys(gids) if g is not None and g >= 0]
        if not label or len(label) < 3 or not gids or is_address(label):
            return
        if kind == 0 and (GENERIC_RE.match(label.lower()) or common[label.lower()] >= GENERIC):
            return
        k = (label.lower(), kind, gids[0])
        if k in seen:
            return
        seen.add(k)
        names.append([label, kind, int(X[gids[0]]), int(Z[gids[0]]), where, *map(int, gids[:40])])

    def at_address(text):
        """The building of 'расположенное по адресу Невский проспект, 28' in an article's first lines."""
        m = re.search(r"по адресу:?\s*([^.;()«»]+?),\s*(?:дом\s*|д\.\s*)?(\d+[а-я]?)\b", text or "")
        if not m:
            return None
        nums = by_key.get(street_key(m[1]))
        gs = nums and (nums.get(m[2]) or next((v for k, v in nums.items() if k.split(" ")[0] == m[2]), None))
        return gs[0] if gs else None

    wk = pd.read_parquet("data/wiki_index.parquet")
    moved = 0
    for k, grp in wk.groupby("wk"):
        w = wiki[int(k)]
        if w.get("label"):
            gids = [gid_of_ident.get(i) for i in grp.identificatie]
            # the article names its address and it is another building: the coordinates fell on a neighbour
            g = at_address((w.get("wiki") or {}).get("extract"))
            if g is not None and g not in gids:
                gids, moved = [g], moved + 1
            add(w["label"], 0, gids)
    # Wikivoyage heritage names and OSM names, without the generic ones ('Жилой дом', 'Флигель', shop chains)
    # shops, kiosks and warehouses keep their OSM names out, unless the name is a mall's or a factory's
    trade = b.building.isin(TRADE) & ~b.name.fillna("").str.match(r"^(ТРК|ТЦ|ТК|БЦ|Бизнес-центр|Завод|Фабрика)", case=False)
    for col in ("wv_name", "name"):
        v = b[col].where(b[col].map(lambda x: isinstance(x, str) and x.strip() != ""))
        if col == "name":
            v = v.where(~trade)
        for g, s in v.dropna().items():
            add(s, 0, [g])
    # places with a story in the layers: their own names, the layer's title as the kind
    for L in json.load(open(OUT / "layers.json")):
        for key, note in L["notes"].items():
            if note.get("name"):
                if L["title"] not in kinds:
                    kinds.append(L["title"])
                add(note["name"], kinds.index(L["title"]), [gid_of_osm.get(key)])
    # people and architects of the graph, at each of their houses
    G = json.load(open(OUT / "graph.json"))
    node = {x["id"]: x for x in G["nodes"]}
    for l in G["links"]:
        e = node.get(l["e"])
        if e and e["type"] in ("person", "architect") and l["p"] in G["places"]:
            pl = G["places"][l["p"]]
            add(e["label"], 1 if e["type"] == "person" else 2, [gid_of_osm.get(k) for k in pl["bags"]], pl["name"])

    (OUT / "search").mkdir(exist_ok=True)
    for old in (OUT / "search").glob("*.json"):
        old.unlink()
    for k, v in shards.items():
        (OUT / "search" / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")))
    out = dict(streets=streets, names=names, kinds=kinds, districts=dnames)
    (OUT / "search.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))

    n_addr = sum(len(v) for s in shards.values() for v in s.values())
    lit = {e[1] for s in shards.values() for v in s.values() for e in v}
    sizes = sorted(((OUT / "search" / f"{k}.json").stat().st_size for k in shards), reverse=True)
    print(f"{len(streets)} streets, {n_addr} house numbers ({n_hoith} from Kon-Tiki before merging), "
          f"{len(lit)} of {n} buildings with an address, {len(names)} names ({moved} articles moved to their address); "
          f"search.json {(OUT / 'search.json').stat().st_size // 1024} KB, {len(shards)} shards, "
          f"largest {sizes[0] // 1024} KB, all {sum(sizes) // 1024} KB")


if __name__ == "__main__":
    main()
