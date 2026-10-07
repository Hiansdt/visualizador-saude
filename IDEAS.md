ROUTE: inline
size:     ~20 files, 3 layers (sources → build → ui), 1 repo
frozen:   no — presentation narrative and next data sources still open
streams:  none — every page reads the same processed CSVs

# Saúde no orçamento federal — ideas

**Pitch:** one dataset (federal health spending, 2000–2026) shown five ways,
so the presentation can move from "how much" to "who cut" to "where" to "on what".

## In the MVP

| Page | Same data, seen as… | Interaction |
|---|---|---|
| Panorama | line over time on colored presidential bands + legal milestones | metric, period, Covid toggle |
| Por governo | year-over-year bars (cuts in red) + per-term growth and level | same filters |
| Mapa | choropleth by state/region, value or change over the period | year slider, per capita/total |
| Composição | stacked area by subfunção (primary care, hospitals…) | R$ vs % share |
| Cortes | budget authorized × committed × paid; Congress vs government proposal; YoY heatmap by SUS area; biggest cuts per action; program series | tabs, year slider |
| Desvios | TCU-judged damage in health TCEs by occurrence year (censored years faded), by category/UF, biggest cases | occurrence vs judgment year |
| Estatística | mean, range, median, mode, variance/SD/CV (pop. and sample) of any variable, per period/president/term, with step-by-step formulas | variable, YoY transform, grouping |
| Dados e método | sources (auto-listed from the registry), caveats, CSV downloads | — |

The sidebar filters are global, so every page re-renders on the same slice.

## Next ideas (pick for the presentation, not committed)

- **Storytelling mode:** a page that walks the 5–6 key moments (EC 29, 2003 dip,
  EC 95 cap, Covid, 2022 drop, 2023 rebound) one per screen. Good for the talk.
- **States + municipalities:** add SIOPS/SICONFI as a source to show that local
  governments carry a growing share of SUS funding.
- **Floor vs actual:** compare spending to the constitutional minimum (EC 29 → EC 86
  → EC 95 → LC 200). This is the sharpest way to show "cuts" under the spending cap.
- **Other functions:** education vs health with the same machinery (função 12).
  It is one constant in `sources/siop.py`.
- **Budgeted vs executed:** a gap chart (dotação vs empenhado) for the
  contingenciamento story. The columns already exist in `anual.csv`.

## Architecture (where to add things)

```
saude_br/sources/   one module per data source (fetch raw → load tables); register in __init__.py
saude_br/build.py   pure functions: source tables → processed datasets
saude_br/pipeline.py  CLI: fetch + build + invariant checks → data/processed/
saude_br/domain/    presidents/terms, metric catalog, geography, term analysis (no Streamlit)
saude_br/ui/        cached data access, global filters, theme, Plotly charts
views/              one file per page;  app.py = navigation + sidebar
```

- **New source:** add a `Source` subclass, register it, then use its tables in `build.py`.
  The "Dados e método" page lists it automatically.
- **New metric:** add a column in `build.py` and an entry in `domain/metrics.py`.
  It then appears in every selector.
- **New page:** add a file in `views/` and one `st.Page` line in `app.py`.

## Run

```
uv sync
uv run streamlit run app.py              # the app reads only data/processed/ (works offline)
uv run python -m saude_br.pipeline       # refresh data (current year is always re-fetched)
uv run pytest                            # data regressions + every page renders
todos                                    # open work stubs in the code
```
