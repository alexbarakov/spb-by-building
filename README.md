# LAYRS: Петербург

3D-карта всех зданий Петербурга по эпохам постройки и слоям истории: Серебряный век, Петербург Пушкина и Достоевского,
блокада, «Последний адрес», дворы-колодцы, парадные, уличный арт, старые бары и другие.
**Карта:** https://stop-token.com/ru/lab/spb/

Некоммерческий проект, сделанный из любопытства. Вдохновлён проектом Саши Богачева
[Paris, building by building](https://paris.bogachev.fr). Движок общий с
[LAYRS: Amsterdam](https://github.com/alexbarakov/amsterdam-by-building): Python-пайплайн → бинарные тайлы → three.js.

**Хотите добавить слой?** См. [CONTRIBUTING.md](CONTRIBUTING.md).

*English: a 3D map of every building in St Petersburg by era and historical context. Non-commercial; the interface
is in Russian. Layers are welcome, see CONTRIBUTING.md.*

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

Сырьё в `data/raw/` (не в git): `spb.osm.pbf` (BBBike, ODbL); `hoith_spb.parquet` — «How old is this house»
(Кон-Тики, ODbL, версия 18.11.2023, вырезка Saint-Petersburg из HOITH_database_231118.gpkg); `gisgkh_spb.parquet` — ГИС ЖКХ из дампа
«Если быть точным» (tochno.st/datasets/gisgkh, CC BY 4.0, сентябрь 2026); `wd_spb.csv`; `pandan_bombing.xlsx`
(PANDAN ЕУСПб, github.com/Julianna-fil/bombing); `plaques.csv`, `districts.json`, `water_relations.json` (OSM/Overpass).

## Данные

- Год известен у 43% зданий: Кон-Тики (28,4 тыс.), ГИС ЖКХ (13 тыс.), Wikidata/ЕГРОКН (2,7 тыс.), OSM (2,1 тыс.).
- citywalls.ru не парсим: robots.txt запрещает ИИ-краулеры. Ссылки на страницы домов берём из Кон-Тики.
  Остальные серые и появляются, когда таймлайн доходит до сегодняшнего дня.
- 1917 в ГИС ЖКХ означает «до революции»: год разносится по 1880–1917 и помечается приблизительным.
- Следующие источники (качает пользователь, Яндекс.Диск и госпорталы не отдают файлы на зарубежный IP):
  «How old is this house» по СПб (disk.yandex.ru/d/-zPLMeUyhtZQow, ODbL, 55 тыс. зданий с годом);
  ТЭП МКД (data.gov.spb.ru, поле комнат в коммуналках); ОКН КГИОП (data.gov.spb.ru); ЕГРОКН (opendata.mkrf.ru).
- Выгрузка BBBike покрывает основную часть города; Кронштадт, Петергоф, Пушкин, Колпино вне её.

## Лицензия

Код — MIT (см. [LICENSE](LICENSE)). Данные остаются под лицензиями источников: OSM и «How old is this house» — ODbL,
ГИС ЖКХ из дампа «Если быть точным» — CC BY 4.0, Wikidata — CC0, Википедия — CC BY-SA, фото Wikimedia Commons — каждое
под своей лицензией, указанной в приложении.
