"""Interesting facts for buildings with a Russian Wikipedia article. First choice: the first item of a section named
«Интересные факты», «Любопытные факты», «Легенды» or «Факты». Otherwise one complete sentence from the «История»
section that has a year and an event (someone lived or died here, a fire, an arrest, the blockade, a first).
Only where the article has one; a fact is always a whole sentence."""
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

from .s06_wiki import get_json

API = "https://ru.wikipedia.org/w/api.php"
SECTION = re.compile(r"^(интересные|любопытные)\s+факты|^легенд|^факты|^интересное", re.I)
HISTORY = re.compile(r"^истори", re.I)
# Only vivid events count: the everyday life of a building (owners, tenants, offices) does not make a fact.
EVENT = re.compile(r"\b(бывал[аи]?|гостил|родил[аи]?с|скончал|умер|убит|расстрел|арестов|снимал[аи]?|снят[аы]?\s|"
                   r"съёмк|пожар|сгорел|взрыв|бомб|снаряд|блокад|госпитал|впервые|перв(?:ый|ая|ое|ые)\s+в\s|"
                   r"легенд|прозв|венчал|провозглас|подписан|писал|написал|сочинил|премьер|дебют|казн|дуэл)", re.I)
# A fact cut at an initial ("… рождения В.") or starting mid-sentence is not a fact.
BROKEN = re.compile(r"\s[А-ЯЁA-Z]\.$|^[^А-ЯЁA-Z0-9«]")
JUNK = re.compile(r"\]\]|\[\[|Файл:|File:|\||\.\s\.|\{|\}|px\b")


def clean(text: str) -> str:
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\{\{.*$", "", t, flags=re.S)  # an unclosed template runs to the end
    t = re.sub(r"\[\[(?:Файл|File|Изображение|Image):[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


SENT = re.compile(r"(?<=[.!?»])\s+(?=[А-ЯЁA-Z«])")


def whole_sentences(text: str, limit: int = 420) -> str | None:
    """As many whole sentences as fit; None if not even one does."""
    out = ""
    for sent in SENT.split(text):
        sent = sent.strip()
        if not sent.endswith((".", "!", "?", "»")):
            break
        if len(out) + len(sent) > limit:
            break
        out = f"{out} {sent}".strip()
    return out if len(out) >= 40 else None


def first_fact(wikitext: str) -> str | None:
    lines = [l for l in wikitext.split("\n") if l.strip() and not l.startswith("=")]
    bullets = [l.lstrip("*# ").strip() for l in lines if l.startswith(("*", "#"))]
    return whole_sentences(clean(bullets[0] if bullets else " ".join(lines)))


def history_fact(wikitext: str) -> str | None:
    text = clean(" ".join(l for l in wikitext.split("\n") if l.strip() and not l.startswith(("=", "*", "#", "|", "{"))))
    best = None
    for sent in SENT.split(text):
        sent = sent.strip()
        if not (60 <= len(sent) <= 300 and sent.endswith(".") and re.search(r"\b1[7-9]\d\d|20[0-2]\d", sent)):
            continue
        score = len(EVENT.findall(sent))
        if score and (best is None or score > best[0]):
            best = (score, sent)
    return best[1] if best else None


def main():
    entries = json.loads(Path("web/data/wiki.json").read_text())
    titles = {i: unquote(e["wiki"]["url"].rsplit("/wiki/", 1)[1]).replace("_", " ")
              for i, e in enumerate(entries) if e.get("wiki") and e["wiki"]["lang"] == "ru"}
    found = 0
    for i, title in titles.items():
        r = get_json(API, {"action": "parse", "page": title, "prop": "sections", "format": "json", "redirects": 1})
        sections = r.get("parse", {}).get("sections", [])
        facts = [s for s in sections if SECTION.search(s["line"])]
        history = [s for s in sections if HISTORY.search(s["line"])]
        fact = None
        for sec, pick in ((facts[:1], first_fact), (history[:1], history_fact)):
            if fact or not sec:
                continue
            w = get_json(API, {"action": "parse", "page": title, "prop": "wikitext", "section": sec[0]["index"],
                               "format": "json", "redirects": 1})
            fact = pick(w.get("parse", {}).get("wikitext", {}).get("*", ""))
        if fact and EVENT.search(fact) and not JUNK.search(fact) and not BROKEN.search(fact):
            entries[i]["fact"] = fact
            found += 1
    Path("web/data/wiki.json").write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(titles)} articles checked, {found} facts")


if __name__ == "__main__":
    main()
