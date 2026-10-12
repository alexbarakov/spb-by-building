"""Resolve every layer to a 64-bit mask per building (two u32 words) and write the layer catalogue."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .layers import LAYERS


def main():
    b = pd.read_parquet("data/buildings.parquet", columns=["identificatie", "year", "date_flag"])
    bag = b.identificatie
    mask = np.zeros(len(b), dtype=np.uint64)
    catalogue, bit = [], 0
    for L in LAYERS:
        members = L["source_fn"]()
        groups = []
        for key, label in L["groups"]:
            hit = bag.map(lambda k: members.get(k) == key).to_numpy(bool)
            mask[hit] |= np.uint64(1) << np.uint64(bit)
            years = b.year[hit & (b.date_flag != 5).to_numpy()].value_counts().sort_index()
            groups.append(dict(key=key, label=label, bit=bit, count=int(hit.sum()),
                               years={str(int(y)): int(n) for y, n in years.items()}))
            bit += 1
        assert bit <= 64, "out of layer bits"
        meta = {k: v for k, v in L.items() if k not in ("source_fn", "groups", "source")}
        meta.update(source=dict(label=L["source"][0], url=L["source"][1]), groups=groups,
                    count=sum(g["count"] for g in groups))
        catalogue.append(meta)
        print(f'{L["id"]:20s}', {g["key"]: g["count"] for g in groups})
    out = pd.DataFrame({"identificatie": b.identificatie,
                        "lay0": (mask & np.uint64(0xFFFFFFFF)).astype(np.uint32),
                        "lay1": (mask >> np.uint64(32)).astype(np.uint32)})
    out.to_parquet("data/layers.parquet")
    Path("web/data/layers.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
