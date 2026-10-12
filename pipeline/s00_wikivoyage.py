"""Wikivoyage «Культурное наследие России/Санкт-Петербург/…» (CC BY-SA 4.0): every {{monument}} template
with its name, address, coordinates, year, author, protection status, EGROKN number and Wikidata id."""
import re
import time

import pandas as pd
import requests

from .city import UA

API = "https://ru.wikivoyage.org/w/api.php"
PREFIX = "Культурное наследие России/Санкт-Петербург"


def pages():
    r = requests.get(API, params={"action": "query", "list": "allpages", "apprefix": PREFIX, "aplimit": 500, "format": "json"},
                     headers=UA, timeout=60).json()
    return [p["title"] for p in r["query"]["allpages"]]


def monuments(wikitext: str):
    for m in re.finditer(r"\{\{monument\s*\|", wikitext):
        end = wikitext.find("\n}}", m.end())
        body = wikitext[m.end():end]
        body = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", body)  # [[target|text]] → text
        body = re.sub(r"\{\{[^{}]*\}\}", "", body)                         # nested templates
        fields = {}
        for k, v in re.findall(r"(?:^|\|)\s*([\w-]+)\s*=\s*([^|]*)", body):
            fields[k] = v.strip()
        yield fields


def main():
    rows = []
    for title in pages():
        r = requests.get(API, params={"action": "parse", "page": title, "prop": "wikitext", "format": "json"},
                         headers=UA, timeout=60).json()
        text = r.get("parse", {}).get("wikitext", {}).get("*", "")
        for f in monuments(text):
            f["page"] = title
            rows.append(f)
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df.to_csv("data/raw/wikivoyage_spb.csv", index=False)
    print(len(df), "monuments;", list(df.columns))


if __name__ == "__main__":
    main()
