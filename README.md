# Петербург, дом за домом

3D-карта всех зданий Петербурга по году постройки. Движок из ~/projects/amsterdam-by-building:
Python-пайплайн → бинарные тайлы → three.js.

## Сборка

```bash
uv sync
uv run python -m pipeline.s00_wikidata    # объекты наследия, даты, архитекторы, фото (Wikidata)
uv run python -m pipeline.s01_osm         # контуры, этажность, даты OSM
uv run python -m pipeline.s02_attributes  # годы, этажность, высоты
uv run python -m pipeline.s05_layers      # слои
uv run python -m pipeline.s06_wiki        # фото Commons и выдержки из Википедии
uv run python -m pipeline.s03_tiles       # тайлы, attrs.bin, city.json
uv run python -m pipeline.s04_water       # вода и суша
uv run python -m pipeline.s07_labels      # подписи улиц и рек
python3 -m http.server 8643 --directory web
```

Сырьё в `data/raw/` (не в git): `spb.osm.pbf` (BBBike, ODbL), `kuk_reformagkh.csv`
(выгрузка «Реформы ЖКХ» 2016 года, github.com/kuk/analyze-reformagkh), `wd_spb.csv`.

## Данные

- Год известен у 13% зданий: реестр МКД 2016 (8,7 тыс.), Wikidata/ЕГРОКН (2,7 тыс.), OSM (2,6 тыс.).
  Остальные серые и появляются, когда таймлайн доходит до сегодняшнего дня.
- 1917 в реестре МКД означает «до революции»: год разносится по 1880–1917 и помечается приблизительным.
- Ждём от пользователя: реестр МКД (Реформа ЖКХ или ГИС ЖКХ, регион 78) и ЕГРОКН (opendata.mkrf.ru, csv.zip).
  Госпорталы не открываются с зарубежного IP.
- Выгрузка BBBike покрывает основную часть города; Кронштадт, Петергоф, Пушкин, Колпино вне её.
