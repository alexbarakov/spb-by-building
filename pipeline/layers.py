"""Layers for Saint Petersburg: historical contexts, each a set of buildings.

A layer has one or more groups; every group takes one bit of a 64-bit mask per building.
Each source function returns {building identificatie: group key}. Layers are listed in historical order.
Sources: Wikidata (CC0) and OpenStreetMap (ODbL).
"""
import re
from functools import cache

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
    ("rossi", "Росси", "Росси"), ("voronikhin", "Воронихин", "Воронихин"), ("stasov", "Стасов", "Стасов"),
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


@layer(
    id="dohodnye", section="Империя", title="Доходные дома", era="1840–1917",
    text=("За полвека до революции население Петербурга выросло в несколько раз, и город застроили "
          "доходными домами: многоэтажными домами с квартирами внаём, парадными фасадами на улицу и "
          "тесными дворами-колодцами за ними."),
    caveat="Только доходные дома, внесённые в реестр наследия и Wikidata; на деле их в несколько раз больше.",
    source=("Wikidata", "https://www.wikidata.org"),
    groups=[("dohodny", "Доходный дом")],
)
def dohodnye():
    w = wikidata()
    hit = w[w.labelRu.str.contains("доходный дом", case=False, na=False)]
    return {b: "dohodny" for b in hit.identificatie}


FAITHS = [
    ("orthodox", "Православные", r"orthodox"), ("oldbel", "Старообрядческие", r"old_believers"),
    ("lutheran", "Лютеранские", r"lutheran"), ("catholic", "Католические", r"catholic"),
    ("armenian", "Армянская", r"armenian"), ("muslim", "Мечеть", r"muslim"),
    ("jewish", "Синагога", r"jewish"), ("buddhist", "Дацан", r"buddhist"),
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
    id="plaques", section="Память", title="Память на стенах", era="1941–1944 и позже",
    text=("Стены Петербурга помнят: доски «Граждане! При артобстреле эта сторона улицы наиболее опасна», "
          "сохранённые со времён блокады, и сотни мемориальных досок тем, кто здесь жил и работал."),
    caveat="Таблички, нанесённые на OpenStreetMap; здание в пределах 15 м от таблички.",
    source=("OpenStreetMap", "https://www.openstreetmap.org"),
    groups=[("blockade", "Блокада"), ("plaque", "Мемориальная доска")],
)
def plaques():
    p = osm_points(r'"memorial"=>"plaque"|блокад')
    text = (p.name.fillna("") + " " + p.other_tags.fillna("")).str.lower()
    p = p.assign(k=np.where(text.str.contains("блокад|артобстрел"), "blockade", "plaque"))
    j = attach_points(buildings(), gpd.GeoDataFrame(p[["k"]], geometry=p.geometry, crs=CRS), 15)
    return dict(zip(j.identificatie, j.k)) | {i: "blockade" for i in j[j.k == "blockade"].identificatie}


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
    ("revealed", "Выявленные", "выявленный"),
]


@layer(
    id="heritage", section="Память", title="Охраняемое наследие", era="Все эпохи",
    text=("Объекты культурного наследия: федеральные охраняет государство, региональные — город; "
          "выявленные ждут решения о включении в реестр."),
    caveat="Объекты, у которых в Wikidata есть номер реестра ЕГРОКН и координаты.",
    source=("Wikidata, ЕГРОКН", "https://www.wikidata.org"),
    groups=[(k, label) for k, label, _ in HERITAGE],
)
def heritage():
    w = wikidata()
    keyed = {}
    for item, h in zip(w.i, w.heritageLabel):
        for k, _, needle in HERITAGE:
            if h and needle in h:
                keyed[item] = k
                break
    return by_items(pd.Series(keyed))
