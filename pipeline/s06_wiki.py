"""Names, photos and article extracts for buildings that have a Wikidata item (P5208 BAG id).

wiki.json: list of {label, wiki: {lang, url, extract} | null, architects, styles, image: {thumb, page,
artist, license, licenseUrl} | null}. data/wiki_index.parquet maps each pand to its entry.
Photos are Wikimedia Commons files with their author and licence, as the Commons API reports them.
"""
import csv
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests

from .city import UA


def get_json(url, params):
    """GET with backoff: the Wikimedia APIs answer bursts with 429 and an HTML page."""
    for attempt in range(6):
        r = requests.post(url, data=params, headers=UA, timeout=60)
        if r.ok and r.headers.get("content-type", "").startswith("application/json"):
            time.sleep(0.3)
            return r.json()
        time.sleep(2 ** attempt)
    r.raise_for_status()
    raise RuntimeError(f"{url}: {r.status_code} {r.text[:200]}")


def batched(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def extracts(lang, titles):
    out = {}
    for chunk in batched(sorted(titles), 20):
        r = get_json(f"https://{lang}.wikipedia.org/w/api.php", {
            "action": "query", "format": "json", "prop": "extracts", "exintro": 1, "explaintext": 1,
            "exsentences": 3, "exlimit": 20, "redirects": 1, "titles": "|".join(chunk)})
        norm = {n["to"]: n["from"] for n in r["query"].get("normalized", []) + r["query"].get("redirects", [])}
        for p in r["query"]["pages"].values():
            t = p.get("title")
            while t in norm:
                t = norm[t]
            if p.get("extract"):
                out[t] = p["extract"].strip()
    return out


def strip_html(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or ""))).strip()


def images(files):
    out = {}
    for chunk in batched(sorted(files), 50):
        r = get_json("https://commons.wikimedia.org/w/api.php", {
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata",
            "iiurlwidth": 500, "titles": "|".join("File:" + f for f in chunk)})
        norm = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        for p in r["query"]["pages"].values():
            ii = (p.get("imageinfo") or [None])[0]
            if not ii:
                continue
            m = ii.get("extmetadata", {})
            key = norm.get(p["title"], p["title"])[5:]
            out[key] = dict(thumb=ii.get("thumburl"), page=ii.get("descriptionurl"),
                            artist=strip_html(m.get("Artist", {}).get("value"))[:80] or None,
                            license=m.get("LicenseShortName", {}).get("value"),
                            licenseUrl=m.get("LicenseUrl", {}).get("value"))
    return out


def title_of(url):
    return unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " ")


def main():
    from .layers import wikidata  # items already matched to buildings
    w = wikidata()
    items = {}
    for r in w.itertuples():
        it = items.setdefault(r.i, dict(ids=set(), label=r.labelRu or r.labelEn, ru=r.ru, en=r.en, image=None,
                                        architects=[a for a in (r.architects or "").split("|") if a],
                                        styles=[x for x in (r.styles or "").split("|") if x]))
        it["ids"].add(r.identificatie)
        if r.image and not it["image"]:
            it["image"] = unquote(r.image.split("|")[0].rsplit("/", 1)[1]).replace("_", " ")

    ex_ru = extracts("ru", {title_of(i["ru"].split("|")[0]) for i in items.values() if i["ru"]})
    ex_en = extracts("en", {title_of(i["en"].split("|")[0]) for i in items.values() if i["en"] and not i["ru"]})
    imgs = images({i["image"] for i in items.values() if i["image"]})
    print(f"extracts ru {len(ex_ru)}, en {len(ex_en)}; images {len(imgs)}")

    entries, index = [], {}
    for it in sorted(items.values(), key=lambda i: (not (i["ru"] or i["en"]), not i["image"])):
        wiki = None
        if it["ru"]:
            url = it["ru"].split("|")[0]
            wiki = dict(lang="ru", url=url, extract=ex_ru.get(title_of(url)))
        elif it["en"]:
            url = it["en"].split("|")[0]
            wiki = dict(lang="en", url=url, extract=ex_en.get(title_of(url)))
        img = imgs.get(it["image"]) if it["image"] else None
        if not (wiki or img or it["label"]):
            continue
        k = len(entries)
        entries.append(dict(label=it["label"], wiki=wiki, architects=it["architects"], styles=it["styles"], image=img))
        for b in it["ids"]:
            index.setdefault(b, k)
    # Hand-checked landmarks: the article named in curated.LANDMARKS replaces whatever the automatic match found.
    from .curated import LANDMARKS
    titles = [l[4] for l in LANDMARKS]
    r = get_json("https://ru.wikipedia.org/w/api.php", {"action": "query", "format": "json", "prop": "extracts|pageimages",
                  "exintro": 1, "explaintext": 1, "exsentences": 3, "exlimit": 20, "piprop": "name", "redirects": 1,
                  "titles": "|".join(titles)})
    norm = {n["to"]: n["from"] for n in r["query"].get("normalized", []) + r["query"].get("redirects", [])}
    pages = {}
    for p in r["query"]["pages"].values():
        t = p.get("title")
        while t in norm:
            t = norm[t]
        pages[t] = p
    files = images({p["pageimage"].replace("_", " ") for p in pages.values() if p.get("pageimage")})
    for ident, lo, hi, label, title, note in LANDMARKS:
        p = pages.get(title, {})
        img = files.get(p.get("pageimage", "").replace("_", " "))
        url = "https://ru.wikipedia.org/wiki/" + requests.utils.quote(p.get("title", title).replace(" ", "_"))
        index[ident] = len(entries)
        entries.append(dict(label=label, wiki=dict(lang="ru", url=url, extract=p.get("extract") or note),
                            architects=[], styles=[], image=img))
    Path("web/data/wiki.json").write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")))
    pd.DataFrame({"identificatie": list(index), "wk": list(index.values())}).to_parquet("data/wiki_index.parquet")
    print(len(entries), "entries for", len(index), "buildings;", Path("web/data/wiki.json").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
