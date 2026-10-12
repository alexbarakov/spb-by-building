"""Memorial plaques (OSM) and the people they name (Wikidata): occupation, years of life, label.
Also every Wikidata place in Petersburg linked to a chosen writer (Pushkin, Dostoevsky, Akhmatova, Blok...)."""
import io
import json
import re

import pandas as pd
import pyogrio
import requests

from .city import OSM, UA

WD = "https://query.wikidata.org/sparql"
WRITERS = {"Q7200": "pushkin", "Q991": "dostoevsky", "Q80440": "akhmatova", "Q178074": "blok",
           "Q187019": "gogol", "Q81082": "nabokov", "Q39803": "brodsky", "Q170509": "mandelstam"}


def sparql(q):
    r = requests.post(WD, data={"query": q}, headers={**UA, "Accept": "text/csv"}, timeout=300)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def main():
    p = pyogrio.read_dataframe(OSM, layer="points", columns=["name", "other_tags"])
    p = p[p.other_tags.fillna("").str.contains('"memorial"=>"plaque"')]
    tags = p.other_tags.fillna("")
    get = lambda k: tags.str.extract(r'"%s"=>"([^"]*)"' % re.escape(k))[0]
    plaques = pd.DataFrame({"lon": p.geometry.x, "lat": p.geometry.y, "name": p.name,
                            "inscription": get("inscription").fillna(get("description")),
                            "subject": get("subject:wikidata"), "wikipedia": get("subject:wikipedia")})
    plaques.to_csv("data/raw/plaques.csv", index=False)

    qids = sorted({q for v in plaques.subject.dropna() for q in v.split(";")})
    people = sparql(f"""SELECT ?p ?label ?born ?died (GROUP_CONCAT(DISTINCT ?occ; separator="|") AS ?occupations)
      (GROUP_CONCAT(DISTINCT ?mov; separator="|") AS ?movements) WHERE {{
      VALUES ?p {{ {" ".join("wd:" + q for q in qids)} }}
      OPTIONAL {{ ?p rdfs:label ?label FILTER(lang(?label)="ru") }}
      OPTIONAL {{ ?p wdt:P569 ?b BIND(YEAR(?b) AS ?born) }}
      OPTIONAL {{ ?p wdt:P570 ?d BIND(YEAR(?d) AS ?died) }}
      OPTIONAL {{ ?p wdt:P106 ?o . ?o rdfs:label ?occ FILTER(lang(?occ)="ru") }}
      OPTIONAL {{ ?p wdt:P135 ?m . ?m rdfs:label ?mov FILTER(lang(?mov)="ru") }}
    }} GROUP BY ?p ?label ?born ?died""")
    people["p"] = people.p.str.rsplit("/", n=1).str[1]
    people.to_csv("data/raw/plaque_people.csv", index=False)

    places = sparql(f"""SELECT ?i ?label ?coord ?w WHERE {{
      VALUES ?w {{ {" ".join("wd:" + q for q in WRITERS)} }}
      ?i ?prop ?w ; wdt:P625 ?coord ; wdt:P131 ?d . ?d wdt:P131* wd:Q656 .
      OPTIONAL {{ ?i rdfs:label ?label FILTER(lang(?label)="ru") }} }}""")
    places["writer"] = places.w.str.rsplit("/", n=1).str[1].map(WRITERS)
    places.to_csv("data/raw/writer_places.csv", index=False)
    print(len(plaques), "plaques;", len(people), "people;", places.groupby("writer").i.nunique().to_dict())


if __name__ == "__main__":
    main()
