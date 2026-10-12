"""Layers for Saint Petersburg: historical contexts, each a set of buildings.

A layer has one or more groups; every group takes one bit of a 64-bit mask per building.
Each source function returns {building identificatie: group key}. Layers are listed in historical order.
Sources: Wikidata (CC0) and OpenStreetMap (ODbL).
"""
import json
import re
from functools import cache

import shapely

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from .city import CRS, OSM, TO_CRS
from .s02_attributes import attach_points

LAYERS = []


def layer(**meta):
    def wrap(fn):
        LAYERS.append(dict(meta, source_fn=fn))
        return fn
    return wrap


@cache
def buildings() -> gpd.GeoDataFrame:
    return gpd.read_parquet("data/buildings.parquet")


@cache
def wikidata() -> gpd.GeoDataFrame:
    """Every Wikidata item with its building, one row per item."""
    w = pd.read_csv("data/raw/wd_spb.csv")
    agg = w.groupby("i").agg(lambda s: "|".join(sorted({x for v in s.dropna() for x in str(v).split("|") if x})))
    ll = agg.coord.str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
    x, y = TO_CRS.transform(ll[0].values, ll[1].values)
    g = gpd.GeoDataFrame(agg.reset_index(), geometry=gpd.points_from_xy(x, y), crs=CRS)
    return attach_points(buildings(), g, 20)


def by_items(keyed: pd.Series) -> dict[str, str]:
    """{item: group} → {building: group}; the first item per building wins."""
    w = wikidata().set_index("i")
    out = {}
    for item, g in keyed.items():
        if item in w.index:
            for b in np.atleast_1d(w.loc[item, "identificatie"]):
                out.setdefault(b, g)
    return out


def osm_points(pattern: str) -> gpd.GeoDataFrame:
    p = pyogrio.read_dataframe(OSM, layer="points", columns=["name", "other_tags"])
    tags = p.other_tags.fillna("").astype(str) + " " + p.name.fillna("")
    p = p[tags.str.contains(pattern, case=False, regex=True)]
    return p.to_crs(CRS)


# ---------- layers ----------

STYLE_GROUPS = [
    ("baroque", "Барокко", r"барокко|baroque"),
    ("stalin", "Сталинский неоклассицизм", r"stalinist|сталинск|^архитектура неоклассицизма"),
    ("classic", "Классицизм и ампир", r"классицизм|ампир|^neoclassicism$|^classicism$"),
    ("eclectic", "Эклектика и русский стиль", r"эклектика|eclectic|русский стиль|неоренессанс|неоготика|кирпичный|brick"),
    ("moderne", "Модерн", r"модерн|art_nouveau|nothern_modern|национальный романтизм"),
    ("constr", "Конструктивизм", r"конструктив|constructivism"),
]


STYLE_ORDER = ["baroque", "classic", "eclectic", "moderne", "constr", "stalin"]


@layer(
    id="styles", section="Архитектура", title="Архитектурные стили", era="1703–1955",
    text=("Петербург строили волнами, и каждая оставила свой стиль: барокко Трезини и Растрелли, строгий "
          "классицизм и ампир Росси, пёструю эклектику доходных домов, северный модерн начала века, "
          "конструктивизм рабочих кварталов и сталинские парадные проспекты."),
    caveat="Стиль указан в OpenStreetMap или Wikidata примерно у 3% зданий.",
    source=("OpenStreetMap и Wikidata", "https://www.wikidata.org"),
    groups=[(k, label) for k, label, _ in sorted(STYLE_GROUPS, key=lambda g: STYLE_ORDER.index(g[0]))],
)
def styles():
    out = {}
    b = buildings()
    for ident, v in zip(b.identificatie, b["building:architecture"]):
        for k, _, pat in STYLE_GROUPS:
            if isinstance(v, str) and re.search(pat, v, re.I):
                out[ident] = k
                break
    w = wikidata()
    for ident, v in zip(w.identificatie, w.styles):
        for k, _, pat in STYLE_GROUPS:
            if v and re.search(pat, v, re.I):
                out.setdefault(ident, k)
                break
    return out


NATIONS = [
    ("italy", "Италия", ("Kingdom of Naples", "Republic of Venice", "Grand Duchy of Tuscany", "Papal States",
                         "Italy", "Kingdom of Italy", "Duchy of Milan", "Republic of Genoa", "Kingdom of Sardinia")),
    ("swiss", "Швейцария", ("Switzerland", "Old Swiss Confederacy")),
    ("france", "Франция", ("France", "Kingdom of France", "French First Republic")),
    ("german", "Германия", ("Germany", "Kingdom of Prussia", "Holy Roman Empire", "German Empire", "Electorate of Saxony",
                            "Kingdom of Saxony", "Kingdom of Bavaria", "Kingdom of Württemberg")),
    ("nordic", "Швеция и Финляндия", ("Sweden", "Grand Duchy of Finland", "Finland")),
]


@layer(
    id="foreign", section="Империя", title="Иностранные зодчие", era="1703–1917",
    text=("Город строили приглашённые мастера. Швейцарец Трезини заложил Петропавловскую крепость, итальянцы "
          "Растрелли, Кваренги и Росси создали дворцы и ансамбли центра, француз Монферран построил Исаакиевский собор, а немецкие и финские зодчие "
          "оставили лютеранские кирхи и модерн Петроградской стороны."),
    caveat=("По подданству архитектора в Wikidata. Многие иностранцы приняли российское подданство "
            "и в слой не попали."),
    source=("Wikidata, архитектор и его подданство", "https://www.wikidata.org"),
    groups=[(k, label) for k, label, _ in NATIONS],
)
def foreign():
    w = wikidata()
    keyed = {}
    for item, countries in zip(w.i, w.archCountries):
        cs = set(countries.split("|")) if countries else set()
        for k, _, names in NATIONS:
            if cs & set(names):
                keyed[item] = k
                break
    return by_items(pd.Series(keyed))


ARCHITECTS = [
    ("trezzini", "Трезини", "Трезини"), ("rastrelli", "Растрелли", "Растрелли"), ("quarenghi", "Кваренги", "Кваренги"),
    ("rossi", "Росси", "Росси"), ("stasov", "Стасов", "Стасов"),
    ("benois", "Бенуа", "Бенуа"), ("lidval", "Лидваль", "Лидваль"),
]


@layer(
    id="architects", section="Архитектура", title="Архитекторы", era="1703–1917",
    text=("Восемь имён, без которых центр Петербурга выглядел бы иначе: от Трезини, первого архитектора "
          "города, до Лидваля, мастера северного модерна."),
    caveat="По данным Wikidata; авторство указано примерно у 600 зданий города.",
    source=("Wikidata", "https://www.wikidata.org"),
    groups=[(k, label) for k, label, _ in ARCHITECTS],
)
def architects():
    w = wikidata()
    keyed = {}
    for item, names in zip(w.i, w.architects):
        for k, _, needle in ARCHITECTS:
            if names and needle in names:
                keyed[item] = k
                break
    return by_items(pd.Series(keyed))


FAITHS = [
    ("orthodox", "Православные", r"orthodox"),
    ("oldbel", "Старообрядческие", r"old_believers"),
    ("western", "Лютеранские, католические, армянская", r"lutheran|catholic|armenian"),
    ("other", "Мечеть, синагога, дацан", r"muslim|jewish|buddhist"),
]


@layer(
    id="faiths", section="Империя", title="Храмы империи", era="1710–1915",
    text=("Столица империи собирала подданных всех вер. На Невском стояли рядом голландская, лютеранская, "
          "католическая и армянская церкви, отчего его звали проспектом веротерпимости, а к 1910-м годам "
          "город получил Соборную мечеть, Большую хоральную синагогу и первый в Европе буддийский дацан."),
    source=("OpenStreetMap", "https://www.openstreetmap.org"),
    groups=[(k, label) for k, label, _ in FAITHS],
)
def faiths():
    b = buildings()
    worship = b[(b.amenity == "place_of_worship") | b.building.isin(["church", "cathedral", "chapel", "mosque", "synagogue", "temple"])]
    out = {}
    for ident, rel, den in zip(worship.identificatie, worship.religion.fillna(""), worship.denomination.fillna("")):
        tag = f"{rel} {den}"
        for k, _, pat in FAITHS:
            if re.search(pat, tag):
                out[ident] = k
                break
        else:
            if rel == "christian":
                out[ident] = "orthodox"
    return out


@layer(
    id="mass", section="Советский город", title="Массовое жильё", era="1956–1990",
    text=("С 1956 года Ленинград расселял коммуналки: сначала пятиэтажками без лифта, «хрущёвками», "
          "потом панельными девяти- и двенадцатиэтажками новых районов. За тридцать лет так переехала "
          "большая часть горожан."),
    caveat="Определено по году постройки и этажности, а не по типовой серии; только дома с известным годом.",
    source=("Реформа ЖКХ, OpenStreetMap", "https://www.openstreetmap.org"),
    groups=[("khrush", "Пятиэтажки 1956–1970"), ("panel", "Высотные дома 1971–1990")],
)
def mass():
    b = buildings()
    dated = b[b.date_flag != 5]
    out = {i: "khrush" for i in dated[dated.year.between(1956, 1970) & dated.floors.between(4, 5)].identificatie}
    out |= {i: "panel" for i in dated[dated.year.between(1971, 1990) & (dated.floors >= 9)].identificatie}
    return out


HERITAGE = [
    ("federal", "Федерального значения", "федерального значения"),
    ("regional", "Регионального значения", "регионального значения"),
    ("revealed", "Выявленные объекты", "выявленный"),
    ("valuable", "Исторически ценные градоформирующие", "градоформирующий"),
    ("signs", "С признаками объекта наследия", "обладающий признаками"),
]


@layer(
    id="heritage", section="Память", title="Уровень охраны наследия", era="Все эпохи",
    text=("Закон делит наследие по уровню охраны. Объекты федерального значения охраняет государство, "
          "регионального — Петербург. Выявленные объекты уже охраняются, но ещё ждут решения о включении в реестр. "
          "Исторически ценные градоформирующие здания — городская категория для рядовой застройки, которая "
          "держит облик центра; их нельзя снести, но можно перестроить внутри."),
    caveat="Объекты, у которых в Wikidata указан статус охраны и есть координаты. Полный реестр ЕГРОКН подключится отдельно.",
    source=("Wikidata, ЕГРОКН", "https://www.wikidata.org"),
    groups=[(k, label) for k, label, _ in HERITAGE],
)
def heritage():
    w = wikidata()
    rank = {k: i for i, (k, _, _) in enumerate(HERITAGE)}
    keyed = {}
    for item, h in zip(w.i, w.heritageLabel):
        for k, _, needle in HERITAGE:
            if h and needle in h and rank[k] < rank.get(keyed.get(item), 99):
                keyed[item] = k
    return by_items(pd.Series(keyed))


# ---------- people, places and events (notes carry the story shown in the building card) ----------

import json
import time
from pathlib import Path

import requests

from .city import ORIGIN, UA
from .curated import DOSTOEVSKY, PUSHKIN, SILVER

GEOCODE_ALT = {
    ("набережная реки Фонтанки", "185"): "185, набережная реки Фонтанки, Санкт-Петербург",
    ("Кузнечный переулок", "5/2"): "музей Достоевского Кузнечный",
    ("набережная канала Грибоедова", "104"): "Средняя Подьяческая улица 15, Санкт-Петербург",
    ("набережная канала Грибоедова", "73"): "набережная канала Грибоедова 73, Санкт-Петербург",
    ("площадь Искусств", "5"): "Итальянская улица 4, Санкт-Петербург",
    ("Марсово поле", "7"): "Марсово поле 7, Санкт-Петербург",
    ("Невский проспект", "15"): "Невский проспект 15, Санкт-Петербург",
}


def geocode(query: str):
    cache_path = Path("data/raw/geocode.json")
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if query not in cache:
        r = requests.get("https://nominatim.openstreetmap.org/search", headers=UA, timeout=30,
                         params={"q": query, "format": "json", "limit": 1, "viewbox": "30.0,60.1,30.7,59.75", "bounded": 1}).json()
        time.sleep(1.1)
        cache[query] = [float(r[0]["lon"]), float(r[0]["lat"])] if r else None
        cache_path.write_text(json.dumps(cache, ensure_ascii=False))
    return cache[query]


def building_at_address(street: str, number: str) -> list[str]:
    b = buildings()
    hit = b[(b["addr:street"] == street) & (b["addr:housenumber"] == number)]
    if len(hit):
        return list(hit.identificatie)
    q = GEOCODE_ALT.get((street, number))
    ll = geocode(q) if q else None
    if not ll:
        print("  not found:", street, number)
        return []
    x, y = TO_CRS.transform(*ll)
    pt = gpd.GeoDataFrame({"k": [0]}, geometry=gpd.points_from_xy([x], [y]), crs=CRS)
    j = attach_points(b, pt, 25)
    return list(j.identificatie)


def centre(ident: str) -> list[float]:
    g = buildings().set_index("identificatie").geometry[ident].centroid
    return [round(g.x - ORIGIN[0], 1), round(-(g.y - ORIGIN[1]), 1)]


def curated(entries) -> tuple[dict, dict]:
    members, notes = {}, {}
    for street, number, group, name, story, query in entries:
        ids = building_at_address(street, number)
        for k, ident in enumerate(ids):
            members[ident] = group
            notes[ident] = dict(story=story, source=f"https://ru.wikipedia.org/w/index.php?search={requests.utils.quote(query)}",
                                **(dict(name=name, at=centre(ident)) if k == 0 else {}))
    return members, notes


@cache
def plaques() -> gpd.GeoDataFrame:
    """Plaques with their buildings and the person each names."""
    p = pd.read_csv("data/raw/plaques.csv")
    x, y = TO_CRS.transform(p.lon.values, p.lat.values)
    g = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(x, y), crs=CRS)
    j = attach_points(buildings(), g, 15)
    people = pd.read_csv("data/raw/plaque_people.csv").drop_duplicates("p").set_index("p")
    j["person"] = j.subject.fillna("").str.split(";").str[0]
    for col in ("label", "born", "died", "occupations", "movements"):
        j[col] = j.person.map(people[col]) if len(people) else None
    return j


def plaque_text(r) -> str:
    text = r.inscription if isinstance(r.inscription, str) and r.inscription.strip() else r["name"]
    return str(text).strip() if isinstance(text, str) else "Мемориальная доска"


def plaque_source(r):
    w = r.wikipedia
    if isinstance(w, str) and ":" in w:
        lang, title = w.split(":", 1)
        return f"https://{lang}.wikipedia.org/wiki/{requests.utils.quote(title.replace(' ', '_'))}"
    return f"https://www.wikidata.org/wiki/{r.person}" if isinstance(r.person, str) and r.person else None


def plaque_notes(rows: pd.DataFrame) -> dict:
    notes = {}
    for ident, grp in rows.groupby("identificatie"):
        texts = [plaque_text(r) for _, r in grp.iterrows()]
        src = next((s for s in (plaque_source(r) for _, r in grp.iterrows()) if s), None)
        notes[ident] = dict(story="Доска: «" + "» · «".join(dict.fromkeys(texts)) + "»", **({"source": src} if src else {}))
    return notes


def people_with(pattern: str, column="label") -> pd.DataFrame:
    j = plaques()
    text = (j.inscription.fillna("") + " " + j["name"].fillna("") + " " + j[column].fillna("")).str.lower()
    return j[text.str.contains(pattern)]


def person_layer(curated_entries, pattern):
    members, notes = curated(curated_entries)
    hits = people_with(pattern)
    for ident, n in plaque_notes(hits).items():
        members.setdefault(ident, "plaque")
        if ident in notes:
            notes[ident]["story"] += " " + n["story"]
        else:
            notes[ident] = n
    return members, notes


@layer(
    id="pushkin", section="Люди и события", title="Пушкинский Петербург", era="1817–1837",
    text=("Пушкин прожил в Петербурге большую часть взрослой жизни и ни разу не имел здесь своего дома: "
          "он снимал квартиры, переезжая почти каждый год. Последняя, на Мойке, стала музеем."),
    caveat="Дома с документированной историей и мемориальные доски из OpenStreetMap.",
    source=("Википедия", "https://ru.wikipedia.org/wiki/Пушкин_в_Петербурге"),
    groups=[("home", "Здесь жил"), ("story", "Связанные истории"), ("plaque", "Мемориальная доска")],
)
def pushkin():
    return person_layer(PUSHKIN, "пушкин")


@layer(
    id="dostoevsky", section="Люди и события", title="Петербург Достоевского", era="1838–1881",
    text=("Достоевский сменил в Петербурге около двадцати квартир и почти всегда выбирал угловые дома. "
          "Его романы привязаны к реальным адресам у Сенной площади, и по ним до сих пор водят экскурсии."),
    caveat="Дома героев романа определены исследователями по описаниям в тексте.",
    source=("Википедия", "https://ru.wikipedia.org/wiki/Петербург_Достоевского"),
    groups=[("home", "Здесь жил"), ("novel", "Дома героев «Преступления и наказания»"), ("plaque", "Мемориальная доска")],
)
def dostoevsky():
    return person_layer(DOSTOEVSKY, "достоевск")


SILVER_MOVES = ("символизм", "акмеизм", "футуризм", "модерн", "модернизм", "русский авангард", "имажинизм")
CREATIVE = ("поэт", "писатель", "прозаик", "драматург", "художник", "композитор", "актёр", "актриса",
            "философ", "литературный критик", "артист балета", "переводчик", "режиссёр")


@layer(
    id="silver", section="Люди и события", title="Серебряный век", era="1890–1922",
    text=("Четверть века перед революцией Петербург был столицей русского модернизма: символисты и акмеисты "
          "собирались на «Башне» Вячеслава Иванова, читали в подвале «Бродячей собаки», спорили в салоне "
          "Мережковских. После 1917 года многие из них эмигрировали, погибли или замолчали."),
    caveat=("Места Серебряного века и мемориальные доски его поэтов, писателей, художников и музыкантов: "
            "людей творческих профессий, родившихся в 1855–1900 годах, по Wikidata."),
    source=("Википедия", "https://ru.wikipedia.org/wiki/Серебряный_век_русской_поэзии"),
    groups=[("venue", "Салоны и кабаре"), ("home", "Здесь жил"), ("plaque", "Мемориальная доска")],
)
def silver():
    members, notes = curated(SILVER)
    j = plaques()
    occ = j.occupations.fillna("").str.lower()
    mov = j.movements.fillna("").str.lower()
    creative = occ.apply(lambda o: any(c in o for c in CREATIVE))
    era = pd.to_numeric(j.born, errors="coerce").between(1855, 1900) & (pd.to_numeric(j.died, errors="coerce") >= 1900)
    hits = j[(creative & era) | mov.apply(lambda m: any(x in m for x in SILVER_MOVES))]
    for ident, n in plaque_notes(hits).items():
        members.setdefault(ident, "plaque")
        notes.setdefault(ident, n)
    return members, notes


OCCUPATIONS = [
    ("literature", "Писатели и поэты", ("писатель", "поэт", "прозаик", "драматург", "романист", "литературный критик")),
    ("science", "Учёные и инженеры", ("физик", "химик", "математик", "учёный", "инженер", "изобретатель", "биолог",
                                      "геолог", "физиолог", "астроном", "врач", "путешественник")),
    ("music", "Музыка, театр, кино", ("композитор", "дирижёр", "пианист", "певец", "певица", "актёр", "актриса",
                                      "артист балета", "кинорежиссёр", "театральный режиссёр")),
    ("art", "Художники и архитекторы", ("художник", "скульптор", "архитектор", "художник-график")),
    ("military", "Военные и полярники", ("военный", "военачальник", "офицер", "адмирал", "лётчик", "военнослужащий")),
]


@layer(
    id="people", section="Люди и события", title="Здесь жили", era="1800–2000",
    text=("Мемориальные доски Петербурга — каталог тех, кто жил и работал в городе: писатели, учёные, "
          "музыканты, художники, полярники. Нажмите на дом, чтобы прочитать надпись."),
    caveat="Доски, нанесённые на OpenStreetMap, с человеком из Wikidata; профессия по первой подходящей в Wikidata.",
    source=("OpenStreetMap и Wikidata", "https://www.openstreetmap.org"),
    groups=[(k, label) for k, label, _ in OCCUPATIONS],
)
def people():
    j = plaques()
    members = {}
    for ident, occ in zip(j.identificatie, j.occupations.fillna("").str.lower()):
        for k, _, words in OCCUPATIONS:
            if any(w in occ for w in words):
                members.setdefault(ident, k)
                break
    return members, plaque_notes(j[j.identificatie.isin(members)])


@layer(
    id="revolution", section="Люди и события", title="Три революции", era="1905–1917",
    text=("Петербург — город трёх революций: 1905 года, Февральской и Октябрьской 1917-го. Советский Ленинград "
          "отметил досками сотни адресов: где собирались подпольщики, где выступал и скрывался Ленин."),
    caveat="Доски, в надписи которых упомянуты революция или Ленин.",
    source=("OpenStreetMap", "https://www.openstreetmap.org"),
    groups=[("lenin", "Ленин"), ("rev", "Революционное движение")],
)
def revolution():
    j = plaques()
    text = (j.inscription.fillna("") + " " + j["name"].fillna("")).str.lower()
    lenin = j[text.str.contains("ленин") & ~text.str.contains("ленинград")]
    rev = j[text.str.contains("революц|большевик|1905|рсдрп|красной гвард|стачк")]
    members = {i: "rev" for i in rev.identificatie} | {i: "lenin" for i in lenin.identificatie}
    return members, plaque_notes(j[j.identificatie.isin(members)])


@layer(
    id="blockade", section="Память", title="Блокада", era="1941–1944",
    text=("872 дня блокады. Предупреждения «Граждане! При артобстреле эта сторона улицы наиболее опасна» "
          "сохраняют на стенах как память; доски отмечают госпитали, штабы и дома, где работали в осаду."),
    caveat="Таблички и доски из OpenStreetMap, связанные с блокадой.",
    source=("Википедия", "https://ru.wikipedia.org/wiki/Блокада_Ленинграда"),
    groups=[("blockade", "Блокадные надписи и доски")],
)
def blockade():
    p = osm_points(r"блокад|артобстрел")
    j = attach_points(buildings(), gpd.GeoDataFrame({"k": ["blockade"] * len(p), "name": p.name.values,
                                                     "inscription": p.other_tags.str.extract(r'"inscription"=>"([^"]*)"')[0].values,
                                                     "wikipedia": None, "person": None},
                                                    geometry=p.geometry.values, crs=CRS), 15)
    return {i: "blockade" for i in j.identificatie}, plaque_notes(j)


@layer(
    id="bombing", section="Память", title="Бомбы и снаряды, осень 1941", era="Сентябрь–октябрь 1941",
    text=("Осенью 1941 года штаб МПВО записывал каждое попадание: адрес, число бомб и снарядов, ущерб, "
          "убитых и раненых. Историк Андрей Рябков и проект PANDAN Европейского университета оцифровали "
          "сводки первых двух месяцев блокады."),
    caveat=("Здание в пределах 20 м от геокодированного адреса сводки; часть адресов привязана к улице, а не к дому. "
            "Только сентябрь–октябрь 1941 года."),
    source=("PANDAN, ЕУСПб: «Бомбардировки Ленинграда»", "http://projects.pandan.eusp.org/bombings"),
    groups=[("fab", "Фугасные бомбы"), ("zab", "Зажигательные бомбы"), ("shell", "Артиллерийские снаряды"),
            ("rebuilt", "Построено после 1941 года на месте попадания")],
)
def bombing():
    return bombing_records()


@cache
def bombing_records():
    x = pd.read_excel("data/raw/pandan_bombing.xlsx")
    x = x[x.coordinates1.notna() & x.coordinates2.notna()].copy()
    lon = pd.to_numeric(x.coordinates1.astype(str).str.replace(",", "."), errors="coerce")
    lat = pd.to_numeric(x.coordinates2.astype(str).str.replace(",", "."), errors="coerce")
    x = x[lon.notna() & lat.notna()]
    lon, lat = lon[x.index], lat[x.index]
    num = lambda c: pd.to_numeric(x[c], errors="coerce").fillna(0)
    x["kind"] = np.where(num("ФАБ") > 0, "fab", np.where(num("ЗАБ") > 0, "zab", "shell"))
    px, py = TO_CRS.transform(lon.values, lat.values)
    g = gpd.GeoDataFrame(x, geometry=gpd.points_from_xy(px, py), crs=CRS)
    j = attach_points(buildings(), g, 20)
    members, notes = {}, {}
    order = {"fab": 0, "shell": 1, "zab": 2}
    b = buildings().set_index("identificatie")
    for ident, grp in j.groupby("identificatie"):
        later = b.date_flag[ident] != 5 and b.year[ident] > 1941
        members[ident] = "rebuilt" if later else min(grp.kind, key=order.get)
        lines = []
        for _, r in grp.head(3).iterrows():
            what = ", ".join(f"{int(v)} {n}" for n, v in (("ФАБ", num("ФАБ")[_]), ("ЗАБ", num("ЗАБ")[_]), ("снар.", num("Снаряд")[_])) if v)
            dmg = str(r["Причиненный ущерб"]) if isinstance(r["Причиненный ущерб"], str) else ""
            dead, hurt = r["Убито"], r["Ранено"]
            people = "; ".join(t for t in (f"убито {dead}" if pd.notna(dead) else "", f"ранено {hurt}" if pd.notna(hurt) else "") if t)
            lines.append(f"{r['Дата']}, {r['Улица, дом']}: {what or 'попадание'}. {dmg} {people}".strip())
        more = f" И ещё записей: {len(grp) - 3}." if len(grp) > 3 else ""
        notes[ident] = dict(story="Сводка МПВО — " + " · ".join(lines) + more, source="http://projects.pandan.eusp.org/bombings")
    return members, notes


# ---------- city fabric ----------

from .s04_water import relation_polygons

CENTRE = ("Центральный район", "Адмиралтейский район", "Василеостровский район", "Петроградский район")


@cache
def districts() -> gpd.GeoDataFrame:
    rel = json.load(open("data/raw/districts.json"))["elements"]
    polys = relation_polygons("data/raw/districts.json")
    return gpd.GeoDataFrame({"name": [e["tags"]["name"] for e in rel]}, geometry=polys, crs=CRS)


@cache
def district_of() -> pd.Series:
    b = buildings()
    pts = gpd.GeoDataFrame({"identificatie": b.identificatie}, geometry=b.geometry.centroid, crs=CRS)
    j = gpd.sjoin(pts, districts(), predicate="within")
    return j.drop_duplicates("identificatie").set_index("identificatie")["name"]


@layer(
    id="courtyards", section="Город", title="Дворы-колодцы", era="1860–1917",
    text=("Доходные дома строили на всю глубину участка, оставляя внутри узкие замкнутые дворы: свет падал в "
          "них только сверху, а окна смотрели в стену напротив. Такие дворы-колодцы — главный образ "
          "Петербурга Достоевского и Некрасова."),
    caveat=("Посчитано по контурам зданий: замкнутые дворы исторического центра шириной до 25 м. "
            "Высота стен по этажности из OpenStreetMap, у части домов она оценена."),
    source=("OpenStreetMap, расчёт по геометрии", "https://www.openstreetmap.org"),
    groups=[("well", "Двор-колодец: стены в полтора раза выше ширины двора"), ("closed", "Тесный замкнутый двор")],
)
def courtyards():
    b = buildings()
    d = district_of()
    centre = b[b.identificatie.map(d).isin(CENTRE)]
    blocks = shapely.union_all(centre.geometry.buffer(0.6).values).buffer(-0.6)
    holes = [shapely.Polygon(r) for p in shapely.get_parts(blocks) if p.geom_type == "Polygon" for r in p.interiors]
    holes = [h for h in holes if 20 < h.area < 3000]
    hg = gpd.GeoDataFrame({"hole": range(len(holes))}, geometry=holes, crs=CRS)
    ring = gpd.GeoDataFrame(hg[["hole"]], geometry=hg.buffer(1.5).difference(hg.geometry), crs=CRS)
    j = gpd.sjoin(centre[["identificatie", "height", "geometry"]], ring, predicate="intersects")
    members, notes = {}, {}
    for hole, grp in j.groupby("hole"):
        poly = holes[hole]
        width = 2 * shapely.maximum_inscribed_circle(poly).length
        height = float(grp.height.median())
        ratio = height / max(width, 1)
        if width > 25 or ratio < 1.0:
            continue
        kind = "well" if ratio >= 1.5 else "closed"
        for ident in grp.identificatie:
            if members.get(ident) != "well":
                members[ident] = kind
                notes[ident] = dict(story=f"Двор шириной около {width:.0f} м и площадью {poly.area:.0f} м²; "
                                          f"стены около {height:.0f} м, в {ratio:.1f} раза выше ширины двора.")
    return members, notes


INDUSTRY_WORDS = r"завод|фабрик|мануфактур|цех\b|цехов|депо\b|электростанц|котельная|газгольдер|склад|пакгауз|мельниц|пивоварен|верф|арсенал"


@layer(
    id="industry", section="Город", title="Промышленный Петербург", era="1800–1960",
    text=("Во второй половине XIX века Петербург стал крупнейшим промышленным городом империи. Выборгская сторона "
          "превратилась в рабочий район: Металлический завод, завод Людвига Нобеля, Арсенал, текстильные "
          "фабрики и казармы для рабочих. Сейчас многие корпуса стали лофтами и креативными пространствами."),
    caveat=("Промышленные здания по разметке OpenStreetMap; Выборгская сторона — Выборгский и Калининский районы. "
            "Памятники промышленной архитектуры — по названию в Wikidata."),
    source=("OpenStreetMap и Wikidata", "https://www.openstreetmap.org"),
    groups=[("heritage", "Заводы и фабрики — памятники"), ("vyborg", "Промышленные здания Выборгской стороны"),
            ("other", "Промышленные здания других районов")],
)
def industry():
    b = buildings()
    d = district_of()
    land = pyogrio.read_dataframe(OSM, layer="multipolygons", columns=["landuse"], where="landuse = 'industrial'").to_crs(CRS)
    pts = gpd.GeoDataFrame({"identificatie": b.identificatie}, geometry=b.geometry.centroid, crs=CRS)
    small = set(b[b.building.isin(["garages", "garage", "shed", "service", "roof", "kiosk", "hut", "container"])].identificatie)
    on_industrial = set(gpd.sjoin(pts, land, predicate="within").identificatie) - small
    typed = set(b[b.building.isin(["industrial", "warehouse", "factory", "manufacture"])].identificatie)
    members = {}
    for ident in typed | on_industrial:
        members[ident] = "vyborg" if d.get(ident) in ("Выборгский район", "Калининский район") else "other"
    w = wikidata()
    hits = w[w.labelRu.str.contains(INDUSTRY_WORDS, case=False, na=False)]
    notes = {}
    for ident, label in zip(hits.identificatie, hits.labelRu):
        members[ident] = "heritage"
        notes[ident] = dict(name=label, story=f"{label} — объект культурного наследия.", at=centre(ident))
    return members, notes


OWNER_RE = re.compile(r"^(Доходный дом|Особняк|Дом|Дворец|Усадьба|Дача)\s+(.+)$", re.I)
NOT_OWNER = re.compile(r"культуры|быта|книги|советов|радио|ветеранов|офицеров|учёных|писателей|художника|композиторов|"
                       r"актёра|журналиста|кино|моды|пионеров|молодёжи|связи|техники|печати|работника|Раскольникова|Пиковой", re.I)


# The words after "Дом" must be a person: initials, or a surname in the genitive.
OWNER_NAME = re.compile(r"^(([А-ЯЁ]\.\s?){1,2}[А-ЯЁ]|[А-ЯЁ][а-яё-]+(ой|ей|а|я|ина|ова|ева|ёва|ича|ских|ского|цкого|ых|их|ера|ля|ца)\b)")
NOT_NAME = re.compile(r"^(Санкт-Петербургск|Германск|Российск|Русск|Императорск|Общества|Товарищества|Городск)", re.I)


@layer(
    id="owners", section="Империя", title="Дома по именам владельцев", era="1740–1917",
    text=("Петербург до сих пор называет дома по старым хозяевам: особняк Кшесинской, дом Мурузи, доходный дом "
          "Толстого, дом Бенуа. Купцы, аристократы и архитекторы строили доходные дома как вложение денег и "
          "подписывали их своими именами на фасадах."),
    caveat="Здания, чьё название в Wikidata образовано от имени владельца; в основном объекты наследия.",
    source=("Wikidata", "https://www.wikidata.org"),
    groups=[("income", "Доходные дома"), ("mansion", "Особняки, дворцы, усадьбы"), ("house", "Дома")],
)
def owners():
    w = wikidata()
    members, notes = {}, {}
    for ident, label, ru in zip(w.identificatie, w.labelRu.fillna(""), w.ru.fillna("")):
        m = OWNER_RE.match(label)
        if not m or NOT_OWNER.search(label) or not OWNER_NAME.match(m.group(2)) or NOT_NAME.match(m.group(2)):
            continue
        kind = m.group(1).lower()
        group = "income" if kind == "доходный дом" else "house" if kind == "дом" else "mansion"
        members[ident] = group
        notes[ident] = dict(story=f"«{label}»." , **({"source": ru.split("|")[0]} if ru else {}))
    return members, notes


@layer(
    id="postwar", section="Память", title="Разрушены и отстроены", era="1941–1960",
    text=("За блокаду в Ленинграде были разрушены или повреждены тысячи зданий. После войны пробелы в центре "
          "заполнили новыми домами, часто сталинскими, вписанными в старую линию застройки: такой дом среди "
          "доходных домов XIX века почти всегда стоит на месте разрушенного."),
    caveat=("Косвенный признак: дома 1944–1960 годов в историческом центре (Центральный, Адмиралтейский, "
            "Василеостровский, Петроградский районы), только с известным годом; и дома после 1941 года у адресов "
            "попаданий из сводок МПВО осени 1941-го."),
    source=("Сводки МПВО (PANDAN, ЕУСПб), OpenStreetMap", "http://projects.pandan.eusp.org/bombings"),
    groups=[("hit", "На месте попадания 1941 года"), ("infill", "Послевоенный дом в историческом центре")],
)
def postwar():
    b = buildings()
    d = b.identificatie.map(district_of())
    dated = b[(b.date_flag != 5) & b.year.between(1944, 1960) & d.isin(CENTRE)]
    members = {i: "infill" for i in dated.identificatie}
    bomb_members, bomb_notes = bombing_records()
    notes = {}
    for ident, g in bomb_members.items():
        if g == "rebuilt":
            members[ident] = "hit"
            notes[ident] = bomb_notes[ident]
    return members, notes


@layer(
    id="communal", section="Советский город", title="Коммуналки", era="1918–наши дни",
    text=("После 1918 года большие квартиры доходных домов «уплотнили»: в каждую комнату заселили по семье, "
          "кухня и уборная стали общими. Так возникли петербургские коммуналки. Их расселяют с 1990-х, но в "
          "городе их до сих пор десятки тысяч, и почти все — в дореволюционных домах центра."),
    caveat=("Косвенный признак: многоквартирные дома, построенные до 1917 года, по реестру домов «Реформы ЖКХ». "
            "Сведений о том, в каких квартирах сейчас коммуналки, в открытых данных нет."),
    source=("Реформа ЖКХ (выгрузка 2016 года)", "https://github.com/kuk/analyze-reformagkh"),
    groups=[("prerev", "Дореволюционный многоквартирный дом")],
)
def communal():
    b = buildings()
    hit = b[(b.year_src == "mkd") & (b.year <= 1917)]
    return {i: "prerev" for i in hit.identificatie}
