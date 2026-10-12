"""Interesting facts for buildings with a Russian Wikipedia article: the first item of a section named
«Интересные факты», «Любопытные факты», «Легенды» or «Факты». Only where the article has one."""
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

from .s06_wiki import get_json

API = "https://ru.wikipedia.org/w/api.php"
SECTION = re.compile(r"^(интересные|любопытные)\s+факты|^легенд|^факты|^интересное", re.I)


def clean(text: str) -> str:
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:Файл|File|Изображение|Image):[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


def first_fact(wikitext: str) -> str | None:
    lines = [l for l in wikitext.split("\n") if l.strip() and not l.startswith("=")]
    bullets = [l.lstrip("*# ").strip() for l in lines if l.startswith(("*", "#"))]
    text = clean(bullets[0] if bullets else " ".join(lines))
    if len(text) < 40:
        return None
    if len(text) > 420:
        cut = text[:420].rsplit(". ", 1)[0]
        text = cut + "." if len(cut) > 80 else text[:419].rsplit(" ", 1)[0] + "…"
    return text


def main():
    entries = json.loads(Path("web/data/wiki.json").read_text())
    titles = {i: unquote(e["wiki"]["url"].rsplit("/wiki/", 1)[1]).replace("_", " ")
              for i, e in enumerate(entries) if e.get("wiki") and e["wiki"]["lang"] == "ru"}
    found = 0
    for i, title in titles.items():
        r = get_json(API, {"action": "parse", "page": title, "prop": "sections", "format": "json", "redirects": 1})
        secs = [s for s in r.get("parse", {}).get("sections", []) if SECTION.search(s["line"])]
        if not secs:
            continue
        w = get_json(API, {"action": "parse", "page": title, "prop": "wikitext", "section": secs[0]["index"],
                           "format": "json", "redirects": 1})
        fact = first_fact(w.get("parse", {}).get("wikitext", {}).get("*", ""))
        if fact:
            entries[i]["fact"] = fact
            found += 1
    Path("web/data/wiki.json").write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(titles)} articles checked, {found} facts")


if __name__ == "__main__":
    main()
