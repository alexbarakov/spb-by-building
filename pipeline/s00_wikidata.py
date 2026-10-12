"""Wikidata: Saint Petersburg's cultural heritage objects (P1483, the EGROKN register id) and other dated
buildings, with date and its precision, architects and their citizenship, style, photo and articles. CC0."""
import io

import pandas as pd
import requests

from .city import UA

Q = """
SELECT ?i ?coord ?okn ?t ?prec ?labelRu ?labelEn ?image ?ru ?en ?heritageLabel
  (GROUP_CONCAT(DISTINCT ?archName; separator="|") AS ?architects)
  (GROUP_CONCAT(DISTINCT ?archCountry; separator="|") AS ?archCountries)
  (GROUP_CONCAT(DISTINCT ?styleName; separator="|") AS ?styles)
WHERE {
  ?i wdt:P131 ?d . ?d wdt:P131* wd:Q656 .
  ?i wdt:P625 ?coord .
  { ?i wdt:P1483 ?okn } UNION { ?i wdt:P31/wdt:P279? wd:Q41176 . ?i wdt:P571 [] }
  OPTIONAL { ?i p:P571/psv:P571 [ wikibase:timeValue ?t ; wikibase:timePrecision ?prec ] }
  OPTIONAL { ?i rdfs:label ?labelRu FILTER(lang(?labelRu)="ru") }
  OPTIONAL { ?i rdfs:label ?labelEn FILTER(lang(?labelEn)="en") }
  OPTIONAL { ?i wdt:P18 ?image }
  OPTIONAL { ?ru schema:about ?i ; schema:isPartOf <https://ru.wikipedia.org/> }
  OPTIONAL { ?en schema:about ?i ; schema:isPartOf <https://en.wikipedia.org/> }
  OPTIONAL { ?i wdt:P1435 ?h . ?h rdfs:label ?heritageLabel FILTER(lang(?heritageLabel)="ru") }
  OPTIONAL { ?i wdt:P84 ?a . ?a rdfs:label ?archName FILTER(lang(?archName)="ru")
             OPTIONAL { ?a wdt:P27 ?ac . ?ac rdfs:label ?archCountry FILTER(lang(?archCountry)="en") } }
  OPTIONAL { ?i wdt:P149 ?s . ?s rdfs:label ?styleName FILTER(lang(?styleName)="ru") }
}
GROUP BY ?i ?coord ?okn ?t ?prec ?labelRu ?labelEn ?image ?ru ?en ?heritageLabel
"""


def main():
    r = requests.get("https://query.wikidata.org/sparql", params={"query": Q}, headers={**UA, "Accept": "text/csv"}, timeout=300)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.to_csv("data/raw/wd_spb.csv", index=False)
    print(len(df), "rows,", df.i.nunique(), "items; dated", df[df.t.notna()].i.nunique(), "; photo", df[df.image.notna()].i.nunique(),
          "; ruwiki", df[df.ru.notna()].i.nunique())


if __name__ == "__main__":
    main()
