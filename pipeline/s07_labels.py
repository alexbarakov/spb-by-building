"""Street, river and canal names from OSM lines, laid flat along their own course.

Each named line is cut into 250 m stretches; every fairly straight stretch gets one label at its middle,
turned along it. Tier 1 (the rivers, canals and main avenues) shows from afar, tier 2 only up close.
Output format matches the viewer: [{name, water, tier, pts: [[x, z, angle, length]]}].
"""
import json
import math
from pathlib import Path

import numpy as np
import pyogrio
import shapely

from .city import CRS, OSM
from .s03_tiles import DAM

STEP = 250.0
HIGHWAYS = {"primary", "secondary", "tertiary", "residential", "pedestrian", "unclassified", "living_street", "trunk"}
TIER1 = {
    "Нева", "Большая Нева", "Малая Нева", "Большая Невка", "Малая Невка", "Средняя Невка", "Фонтанка",
    "Мойка", "канал Грибоедова", "Обводный канал", "Крюков канал", "Екатерингофка", "Карповка", "Охта",
    "Невский проспект", "Литейный проспект", "Садовая улица", "Гороховая улица", "Вознесенский проспект",
    "Московский проспект", "Каменноостровский проспект", "Большой проспект П.С.", "Большой проспект В.О.",
    "Средний проспект В.О.", "Лиговский проспект", "Владимирский проспект", "Загородный проспект",
    "Суворовский проспект", "Дворцовая набережная", "Английская набережная", "Университетская набережная",
    "Кронверкский проспект", "Петроградская набережная", "набережная Кутузова", "проспект Обуховской Обороны",
    "Сампсониевский проспект", "Лесной проспект", "Измайловский проспект", "Невская губа",
}


def placements(line):
    n = max(1, int(line.length // STEP))
    out = []
    for k in range(n):
        a, b = line.interpolate(k * STEP), line.interpolate(min((k + 1) * STEP, line.length))
        seg = shapely.ops.substring(line, k * STEP, min((k + 1) * STEP, line.length))
        chord = a.distance(b)
        if chord < 80 or chord < 0.85 * seg.length:
            continue
        mid = seg.interpolate(0.5, normalized=True)
        ang = math.degrees(math.atan2(-(b.y - a.y), b.x - a.x))
        ang = (ang + 90) % 180 - 90
        out.append([round(mid.x - DAM[0], 1), round(-(mid.y - DAM[1]), 1), round(ang, 1), round(chord)])
    return out


def main():
    import shapely.ops  # noqa: F401
    lines = pyogrio.read_dataframe(OSM, layer="lines", columns=["name", "highway", "waterway"])
    lines = lines[lines.name.notna() & (lines.highway.isin(HIGHWAYS) | lines.waterway.isin(["river", "canal"]))]
    lines = lines.to_crs(CRS)
    labels = []
    for (name, water), grp in lines.groupby([lines.name, lines.waterway.notna()]):
        merged = shapely.line_merge(shapely.union_all(grp.geometry.values))
        pts = [p for part in shapely.get_parts(merged) for p in placements(part)]
        if not pts:
            continue
        kept = []
        for p in sorted(pts, key=lambda p: -p[3]):
            if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 400 ** 2 for q in kept):
                kept.append(p)
        labels.append(dict(name=name, water=bool(water), tier=1 if name in TIER1 else 2, pts=kept))
    Path("web/data/labels.json").write_text(json.dumps(labels, ensure_ascii=False, separators=(",", ":")))
    print(len(labels), "names,", sum(len(l["pts"]) for l in labels), "placements,",
          sum(l["tier"] == 1 for l in labels), "tier 1;", Path("web/data/labels.json").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
