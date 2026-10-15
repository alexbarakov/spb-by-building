"""Находит здания ответа для каждого шага квеста (web/data/quests.json) и проверяет, что шаг решаем.

Ответ-история берёт здания этой истории из web/data/layers.json (по названию) и получает вторую подсказку —
направление и расстояние от Дворцовой площади, посчитанные здесь, чтобы не ошибиться. Ответ-правило остаётся
правилом: зритель проверяет здание по битам групп слоёв и году. Шаг без истории, без фото для фото-загадки или с
правилом без зданий — ошибка; квест с ошибкой не попадает в файл.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .quests import QUESTS

CENTRE = "Дворцовой площади"   # the origin of the local frame
DIRS = ["востоку", "северо-востоку", "северу", "северо-западу", "западу", "юго-западу", "югу", "юго-востоку"]


def direction_hint(x, z):
    d = math.hypot(x, z)
    if d < 150:
        return dict(ru="Здание у самой Дворцовой площади.")
    side = DIRS[round(math.degrees(math.atan2(-z, x)) / 45) % 8]
    dist = f"{int(round(d / 50) * 50)} м" if d < 1000 else f"{str(round(d / 100) / 10).replace('.', ',')} км"
    return dict(ru=f"Около {dist} к {side} от {CENTRE}.")


def key_of(bag):
    return f"r{bag[1:]}" if bag.startswith("-") else f"w{bag}"


def main():
    layers = {L["id"]: L for L in json.load(open("web/data/layers.json"))}
    wiki = json.load(open("web/data/wiki.json"))
    wk = pd.read_parquet("data/wiki_index.parquet").set_index("identificatie").wk
    b = pd.read_parquet("data/buildings.parquet", columns=["identificatie", "year"])
    lay = pd.read_parquet("data/layers.parquet")
    assert (lay.identificatie.to_numpy() == b.identificatie.to_numpy()).all()
    mask = (lay.lay1.to_numpy(np.uint64) << np.uint64(32)) | lay.lay0.to_numpy(np.uint64)
    out, problems = [], []
    for q in QUESTS:
        steps = []
        for i, s in enumerate(q["steps"]):
            kind, *arg = s["answer"]
            step = {k: v for k, v in s.items() if k != "answer"}
            where = f'{q["id"]} шаг {i + 1}'
            if kind == "story":
                layer, name = arg
                notes = [(k, n) for k, n in layers.get(layer, {}).get("notes", {}).items() if n.get("name") == name and n.get("at")]
                if not notes:
                    problems.append(f"{where}: нет истории «{name}» в слое {layer}")
                    continue
                bags = [k for k, _ in notes]
                n = notes[0][1]
                step["answer"] = dict(bags=bags)
                step["found"] = dict(name=n["name"], story=n["story"], source=n.get("source"))
                auto = direction_hint(*np.mean([m["at"] for _, m in notes], axis=0))
                step["hints"] = [auto] + s["hints"] if q["level"] == 3 else s["hints"] + [auto]
                if s.get("photo"):
                    photo = next((wiki[wk[key_of(k)]]["image"] for k in bags if key_of(k) in wk.index and wiki[wk[key_of(k)]].get("image")), None)
                    if not photo:
                        problems.append(f"{where}: нет фото для «{name}»")
                        continue
                    step["photo"] = photo
            else:
                rule, ok, cond = arg[0], np.ones(len(b), bool), {}
                if "before" in rule:
                    ok &= (b.year.to_numpy() > 0) & (b.year.to_numpy() < rule["before"]); cond["before"] = rule["before"]
                if "after" in rule:
                    ok &= b.year.to_numpy() > rule["after"]; cond["after"] = rule["after"]
                bits = []
                for layer, group in rule.get("groups", []):
                    g = next((g for g in layers.get(layer, {}).get("groups", []) if g["key"] == group), None)
                    if not g:
                        problems.append(f"{where}: нет группы {layer}/{group}"); ok[:] = False; break
                    ok &= ((mask >> np.uint64(g["bit"])) & np.uint64(1)).astype(bool)
                    bits.append(g["bit"])
                if bits:
                    cond["bits"] = bits
                if not ok.any():
                    problems.append(f"{where}: ни одно здание не подходит под {rule}")
                    continue
                step["answer"] = cond
                step["count"] = int(ok.sum())
            steps.append(step)
        if len(steps) == len(q["steps"]):
            out.append(dict({k: v for k, v in q.items() if k != "steps"}, steps=steps))
        print(f'{q["id"]:10s} уровень {q["level"]}  {len(steps)}/{len(q["steps"])}')
    for p in problems:
        print("ошибка:", p)
    Path("web/data/quests.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), "квестов")


if __name__ == "__main__":
    main()
