"""Gráficos Plotly. Cada função recebe dados já filtrados e devolve uma figura."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from saude_br.domain.governments import EVENTS, TERMS
from saude_br.domain.metrics import Metric
from saude_br.ui.theme import NEG, POS, SEQUENTIAL, diverging_scale, palette, president_color, style


def _pct(v: float) -> str:
    return f"{100 * v:+.1f}%".replace(".", ",")


def _padded_range(values: pd.Series) -> list[float]:
    """Folga nas pontas para os rótulos de fora da barra não serem cortados."""
    lo, hi = min(0.0, values.min()), max(0.0, values.max())
    pad = 0.28 * (hi - lo)
    return [lo - pad if lo < 0 else 0, hi + pad if hi > 0 else 0]


def add_term_bands(fig, start: int, end: int, neutral: bool = False, row=None, col=None) -> None:
    """Faixa por mandato com o nome escrito em cima.

    neutral=True usa cinza alternado: para gráficos com várias séries coloridas,
    onde a cor do presidente competiria com a cor das séries.
    """
    p = palette()
    for i, t in enumerate(TERMS):
        x0, x1 = max(t.start, start), min(t.end, end)
        if x0 > x1:
            continue
        color = (p["grid"] if i % 2 else p["surface"]) if neutral else president_color(t.president)
        cell = {} if row is None else {"row": row, "col": col}
        fig.add_vrect(x0=x0 - 0.5, x1=x1 + 0.5, fillcolor=color, opacity=0.6 if neutral else 0.12,
                      line_width=0, layer="below", **cell)
        if row is not None:
            continue  # small multiples: sem rótulos, os títulos já ocupam o topo
        fig.add_annotation(x=(x0 + x1) / 2, y=1, yref="paper", yanchor="bottom", text=t.key,
                           showarrow=False, font=dict(size=11, color=palette()["ink_2"]))


def add_events(fig, start: int, end: int) -> None:
    p = palette()
    for year, text in EVENTS:
        if start <= year <= end:
            fig.add_vline(x=year, line_width=1, line_color=p["muted"], layer="below")
            fig.add_annotation(x=year, y=0.02, yref="paper", text=text, textangle=-90,
                               xanchor="left", yanchor="bottom", xshift=2, showarrow=False,
                               font=dict(size=10, color=p["muted"]))


def timeline(anual: pd.DataFrame, metric: Metric, sem_covid: bool, events: bool = True) -> go.Figure:
    p = palette()
    fig = go.Figure()
    start, end = int(anual["ano"].min()), int(anual["ano"].max())
    add_term_bands(fig, start, end)
    if events:
        add_events(fig, start, end)

    covid_split = sem_covid and metric.column_sem_covid
    main = "Corrigido pela inflação" if metric.nominal_column else metric.label
    series = [(metric.col(sem_covid), f"{main}, sem Covid" if covid_split else main, p["ink"], 2)]
    if covid_split:
        series.insert(0, (metric.column, f"{main}, com Covid", p["muted"], 1))
    if metric.nominal_column:
        nominal = metric.nominal_column + ("_sem_covid" if covid_split else "")
        series.append((nominal, "Sem correção (valor da época)", p["series"][6], 1))
    for col, name, color, width in series:
        y = anual[col] / metric.scale
        partial = anual["ano_parcial"]
        fig.add_trace(go.Scatter(
            x=anual["ano"], y=y, name=name, mode="lines+markers",
            line=dict(color=color, width=width),
            marker=dict(size=8, color=color, symbol=["circle-open" if x else "circle" for x in partial],
                        line=dict(width=2, color=p["surface"] if width == 2 else color)),
            customdata=[metric.fmt(v) + (" (parcial)" if pa else "") for v, pa in zip(anual[col], partial)],
            hovertemplate="%{customdata}<extra>" + name + "</extra>",
        ))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(rangemode="tozero", ticksuffix=f" {metric.unit}" if metric.unit == "%" else "")
    fig.update_xaxes(dtick=2)
    return style(fig, height=460, legend=len(series) > 1)


def yoy_bars(anual: pd.DataFrame, column: str, covid_note: bool = False) -> go.Figure:
    """Variação ano a ano: onde estão os cortes. Recebe só anos fechados."""
    df = anual.sort_values("ano").copy()
    df["var"] = df[column].pct_change()
    df = df.dropna(subset=["var"])
    fig = go.Figure()
    add_term_bands(fig, int(df["ano"].min()), int(df["ano"].max()))
    fig.add_trace(go.Bar(
        x=df["ano"], y=100 * df["var"], marker_color=[POS if v >= 0 else NEG for v in df["var"]],
        marker_cornerradius=4,
        customdata=[_pct(v) for v in df["var"]],
        hovertemplate="%{x}: %{customdata}<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1, line_color=palette()["axis"])
    if covid_note:
        for year, text in ((2020, "gasto Covid"), (2022, "fim do gasto Covid")):
            if year in set(df["ano"]):
                v = 100 * df.loc[df["ano"] == year, "var"].iloc[0]
                fig.add_annotation(x=year, y=v, text=text, showarrow=False, yshift=12 if v >= 0 else -12,
                                   font=dict(size=10, color=palette()["ink_2"]))
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(dtick=2)
    return style(fig, height=340, legend=False)


def term_change_bars(changes: pd.DataFrame) -> go.Figure:
    df = changes.iloc[::-1]  # primeiro mandato no topo
    labels = [f"{m} ({b}→{e}){' *' if inc else ''}" for m, b, e, inc
              in zip(df["mandato"], df["ano_base"], df["ano_fim"], df["incompleto"])]
    fig = go.Figure(go.Bar(
        y=labels, x=100 * df["var_anual"], orientation="h",
        marker_color=[POS if v >= 0 else NEG for v in df["var_anual"]], marker_cornerradius=4,
        text=[_pct(v) + "/ano" for v in df["var_anual"]], textposition="outside", cliponaxis=False,
        textfont_color=palette()["ink_2"],
        customdata=[_pct(v) for v in df["var_total"]],
        hovertemplate="%{y}<br>%{text} · total no mandato %{customdata}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color=palette()["axis"])
    fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=palette()["grid"],
                     range=_padded_range(100 * df["var_anual"]))
    fig.update_layout(bargap=0.35)
    return style(fig, height=380, legend=False)


def term_level_bars(changes: pd.DataFrame, metric: Metric) -> go.Figure:
    df = changes.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=df["mandato"], x=df["media"] / metric.scale, orientation="h",
        marker_color=[president_color(p) for p in df["presidente"]], marker_cornerradius=4,
        text=[metric.fmt(v) for v in df["media"]], textposition="outside", cliponaxis=False,
        textfont_color=palette()["ink_2"],
        hovertemplate="%{y}: %{text} (média anual)<extra></extra>",
    ))
    fig.update_xaxes(showgrid=True, gridcolor=palette()["grid"], range=_padded_range(df["media"] / metric.scale))
    fig.update_layout(bargap=0.35)
    return style(fig, height=380, legend=False)


def choropleth(df: pd.DataFrame, geojson: dict, value: str, hover: list[str],
               diverging: bool = False, range_: tuple | None = None) -> go.Figure:
    p = palette()
    fig = go.Figure(go.Choropleth(
        geojson=geojson, featureidkey="properties.codarea",
        locations=df["cod"].astype(str), z=df[value],
        colorscale=diverging_scale() if diverging else [[i / (len(SEQUENTIAL) - 1), c] for i, c in enumerate(SEQUENTIAL)],
        zmid=0 if diverging else None,
        zmin=range_[0] if range_ else None, zmax=range_[1] if range_ else None,
        marker_line_color=p["surface"], marker_line_width=1,
        customdata=df[hover], hovertemplate="<br>".join(f"%{{customdata[{i}]}}" for i in range(len(hover))) + "<extra></extra>",
        colorbar=dict(thickness=10, outlinewidth=0, tickfont_color=p["muted"], len=0.7),
    ))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig = style(fig, height=560, legend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def composition(sub: pd.DataFrame, names: list[str], share: bool) -> go.Figure:
    """Área empilhada por subfunção; `names` em ordem fixa de cor (maior primeiro).

    `sub` precisa da coluna `valor` (R$ bi ou % do ano, conforme `share`).
    """
    p = palette()
    fig = go.Figure()
    for i, name in enumerate(names):
        s = sub[sub["grupo"] == name].sort_values("ano")
        color = p["other"] if name == "Outras" else p["series"][i]
        fig.add_trace(go.Scatter(
            x=s["ano"], y=s["valor"], name=name, stackgroup="one", mode="lines",
            line=dict(width=1, color=p["surface"]), fillcolor=color,
            hovertemplate=f"{name}: " + ("%{y:.1f}%" if share else "R$ %{y:.1f} bi") + "<extra></extra>",
        ))
    fig.update_layout(hovermode="x unified", legend_traceorder="normal")
    fig.update_yaxes(ticksuffix="%" if share else "", rangemode="tozero")
    fig.update_xaxes(dtick=2)
    return style(fig, height=460)


# --- Cortes ----------------------------------------------------------------

def execution_lines(ex: pd.DataFrame) -> go.Figure:
    """Autorizado, empenhado e pago, em R$ bi corrigidos."""
    p = palette()
    fig = go.Figure()
    add_term_bands(fig, int(ex["ano"].min()), int(ex["ano"].max()), neutral=True)
    for col, name, color in (("dotacao_atual_real", "Autorizado (lei + créditos)", p["series"][0]),
                             ("empenhado_real", "Empenhado (comprometido)", p["ink"]),
                             ("pago_real", "Pago no próprio ano", p["series"][2])):
        fig.add_trace(go.Scatter(x=ex["ano"], y=ex[col] / 1e9, name=name, mode="lines+markers",
                                 line=dict(color=color, width=2), marker=dict(size=6, color=color),
                                 hovertemplate=name + ": R$ %{y:.1f} bi<extra></extra>"))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(rangemode="tozero", ticksuffix=" bi")
    fig.update_xaxes(dtick=2)
    return style(fig, height=400)


def share_bars(ex: pd.DataFrame, column: str, label: str, color: str) -> go.Figure:
    """Barras de um percentual por ano, uma cor só (a série é única)."""
    fig = go.Figure()
    add_term_bands(fig, int(ex["ano"].min()), int(ex["ano"].max()))
    fig.add_trace(go.Bar(x=ex["ano"], y=ex[column], marker_color=color, marker_cornerradius=4,
                         hovertemplate="%{x}: %{y:.1f}% " + label + "<extra></extra>"))
    fig.add_hline(y=0, line_width=1, line_color=palette()["axis"])
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(dtick=2)
    return style(fig, height=320, legend=False)


def area_heatmap(pivot: pd.DataFrame, masked: pd.DataFrame) -> go.Figure:
    """Variação real ano a ano por área (linhas) e ano (colunas)."""
    z = pivot.where(~masked)
    text = [[("*" if m else ("" if pd.isna(v) else f"{v:+.0f}%")) for v, m in zip(zr, mr)]
            for zr, mr in zip(z.values, masked.values)]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=pivot.columns, y=pivot.index, text=text, texttemplate="%{text}",
        textfont=dict(size=10), colorscale=diverging_scale(), zmid=0, zmin=-30, zmax=30,
        xgap=2, ygap=2, colorbar=dict(thickness=10, outlinewidth=0, ticksuffix="%", len=0.8),
        hovertemplate="%{y}<br>%{x}: %{z:+.1f}%<extra></extra>",
    ))
    fig.update_xaxes(dtick=1, tickangle=-90)
    fig.update_yaxes(autorange="reversed")
    return style(fig, height=80 + 42 * len(pivot), legend=False)


def drop_bars(df: pd.DataFrame) -> go.Figure:
    """Maiores quedas em R$ milhões (uma série: cor de queda)."""
    d = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=d["rotulo"], x=d["queda_mi"], orientation="h", marker_color=NEG, marker_cornerradius=4,
        text=[f"R$ {v:,.0f} mi".replace(",", ".") for v in d["queda_mi"]], textposition="outside",
        cliponaxis=False, textfont_color=palette()["ink_2"],
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    fig.update_xaxes(range=_padded_range(d["queda_mi"]), showgrid=True, gridcolor=palette()["grid"])
    fig.update_layout(bargap=0.3)
    return style(fig, height=60 + 34 * len(d), legend=False)


def program_multiples(series: dict[str, pd.DataFrame], start: int, end: int) -> go.Figure:
    """Um gráfico pequeno por programa, cada um com sua escala."""
    p = palette()
    names = list(series)
    cols = 3
    rows = -(-len(names) // cols)
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=names, horizontal_spacing=0.06,
                        vertical_spacing=0.16)
    for i, name in enumerate(names):
        r, c = i // cols + 1, i % cols + 1
        d = series[name]
        add_term_bands(fig, start, end, row=r, col=c)
        fig.add_trace(go.Scatter(x=d["ano"], y=d["emp_real"] / 1e9, mode="lines+markers", name=name,
                                 line=dict(color=p["ink"], width=2), marker=dict(size=5, color=p["ink"]),
                                 hovertemplate="%{x}: R$ %{y:.2f} bi<extra>" + name + "</extra>"),
                      row=r, col=c)
        fig.update_yaxes(rangemode="tozero", ticksuffix=" bi", row=r, col=c)
        fig.update_xaxes(range=[start - 0.5, end + 0.5], row=r, col=c)
    fig.update_annotations(font_size=12)
    return style(fig, height=300 * rows, legend=False)


# --- Desvios ---------------------------------------------------------------

DESVIO_COLORS = {"Indícios de desvio ou fraude": 1, "Omissão ou não comprovação": 0, "Outras irregularidades": None}


def desvio_bars(df: pd.DataFrame, x: str, censored: dict[int, float] | None = None) -> go.Figure:
    """Barras empilhadas por categoria, em R$ milhões corrigidos.

    censored: ano -> % estimado já julgado; anos abaixo de 70% ficam apagados.
    """
    p = palette()
    fig = go.Figure()
    start, end = int(df[x].min()), int(df[x].max())
    add_term_bands(fig, start, end)
    faded = {y for y, v in (censored or {}).items() if v < 70}
    for cat, slot in DESVIO_COLORS.items():
        d = df[df["categoria"] == cat].sort_values(x)
        color = p["other"] if slot is None else p["series"][slot]
        fig.add_trace(go.Bar(
            x=d[x], y=d["valor_real"] / 1e6, name=cat, marker_color=color, marker_cornerradius=2,
            marker_opacity=[0.35 if y in faded else 1 for y in d[x]],
            marker_line=dict(width=1, color=p["surface"]),
            hovertemplate=cat + ": R$ %{y:.1f} mi<extra>%{x}</extra>",
        ))
    if faded:
        first = min(faded)
        fig.add_vrect(x0=first - 0.5, x1=end + 0.5, fillcolor=p["grid"], opacity=0.5, line_width=0, layer="below")
        fig.add_annotation(x=(first + end) / 2, y=0.92, yref="paper", showarrow=False,
                           text="ainda em julgamento", font=dict(size=11, color=p["ink_2"]))
    fig.update_layout(barmode="stack", hovermode="x unified", bargap=0.2, legend_traceorder="normal")
    fig.update_yaxes(ticksuffix=" mi")
    fig.update_xaxes(dtick=2)
    return style(fig, height=440)


def uf_bars(df: pd.DataFrame) -> go.Figure:
    d = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=d["uf"], x=d["valor_real"] / 1e6, orientation="h", marker_color=palette()["series"][0],
        marker_cornerradius=4, text=[f"R$ {v / 1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
                                     for v in d["valor_real"]],
        textposition="outside", cliponaxis=False, textfont_color=palette()["ink_2"],
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    fig.update_xaxes(range=_padded_range(d["valor_real"] / 1e6), showgrid=True, gridcolor=palette()["grid"])
    fig.update_layout(bargap=0.3)
    return style(fig, height=60 + 26 * len(d), legend=False)


# --- Estatística -------------------------------------------------------------

def series_with_mean(df: pd.DataFrame, mean: float, sd: float, unit: str) -> go.Figure:
    """Valor de cada ano (barra) com a média e a faixa média ± 1 desvio padrão."""
    p = palette()
    fig = go.Figure()
    add_term_bands(fig, int(df["ano"].min()), int(df["ano"].max()))
    fig.add_hrect(y0=mean - sd, y1=mean + sd, fillcolor=p["grid"], opacity=0.7, line_width=0, layer="below")
    fig.add_trace(go.Bar(x=df["ano"], y=df["valor"], marker_color=p["series"][0], marker_cornerradius=4,
                         hovertemplate="%{x}: %{y:.2f} " + unit + "<extra></extra>"))
    fig.add_hline(y=mean, line_width=2, line_color=p["ink"])
    fig.add_annotation(x=1, xref="paper", y=mean, xanchor="right", yanchor="bottom", showarrow=False,
                       text="média", font=dict(size=11, color=p["ink"]))
    fig.add_annotation(x=1, xref="paper", y=mean + sd, xanchor="right", yanchor="bottom", showarrow=False,
                       text="média + 1 DP", font=dict(size=10, color=p["ink_2"]))
    fig.update_xaxes(dtick=2)
    return style(fig, height=380, legend=False)


def group_dots(df: pd.DataFrame, groups: list[str], means: dict[str, float], unit: str) -> go.Figure:
    """Cada ano é um ponto na coluna do seu grupo; o traço marca a média do grupo."""
    p = palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["grupo"], y=df["valor"], mode="markers", name="ano",
        marker=dict(size=10, color=p["series"][0], line=dict(width=2, color=p["surface"])),
        customdata=df["ano"], hovertemplate="%{customdata}: %{y:.2f} " + unit + "<extra>%{x}</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=groups, y=[means[g] for g in groups], mode="markers", name="média do grupo",
        marker=dict(symbol="line-ew-open", size=34, color=p["ink"], line=dict(width=3)),
        hovertemplate="média: %{y:.2f} " + unit + "<extra>%{x}</extra>",
    ))
    fig.update_xaxes(categoryorder="array", categoryarray=groups)
    fig.update_yaxes(gridcolor=p["grid"])
    return style(fig, height=380)
