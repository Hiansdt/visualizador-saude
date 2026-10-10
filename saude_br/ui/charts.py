"""Gráficos Plotly. Cada função recebe dados já prontos e devolve uma figura."""

import pandas as pd
import plotly.graph_objects as go

from saude_br.domain.governments import TERMS
from saude_br.domain.stats import ModalClass
from saude_br.ui.fmt import value
from saude_br.ui.theme import SEQUENTIAL, diverging_scale, palette, president_color, style


def add_term_bands(fig, start: int, end: int, neutral: bool = False) -> None:
    """Faixa por mandato com o nome escrito em cima.

    neutral=True usa cinza alternado: com várias séries coloridas, a cor do
    presidente competiria com a cor das séries.
    """
    p = palette()
    for i, t in enumerate(TERMS):
        x0, x1 = max(t.start, start), min(t.end, end)
        if x0 > x1:
            continue
        color = (p["grid"] if i % 2 else p["surface"]) if neutral else president_color(t.president)
        fig.add_vrect(x0=x0 - 0.5, x1=x1 + 0.5, fillcolor=color, opacity=0.6 if neutral else 0.12,
                      line_width=0, layer="below")
        fig.add_annotation(x=(x0 + x1) / 2, y=1, yref="paper", yanchor="bottom", text=t.key,
                           showarrow=False, font=dict(size=11, color=p["ink_2"]))


def stat_timeline(df: pd.DataFrame, series: list[tuple[str, str]], unit: str, decimals: int,
                  ano: int | None = None) -> go.Figure:
    """Uma ou mais medidas ano a ano. series = [(coluna, rótulo)]."""
    p = palette()
    fig = go.Figure()
    start, end = int(df["Ano"].min()), int(df["Ano"].max())
    add_term_bands(fig, start, end, neutral=len(series) > 1)
    colors = [p["ink"]] if len(series) == 1 else p["series"]
    for (col, label), color in zip(series, colors):
        fig.add_trace(go.Scatter(
            x=df["Ano"], y=df[col], name=label, mode="lines+markers",
            line=dict(color=color, width=2), marker=dict(size=7, color=color),
            customdata=[value(v, unit, decimals) for v in df[col]],
            hovertemplate="%{customdata}<extra>" + label + "</extra>",
        ))
    if ano is not None:
        fig.add_vline(x=ano, line_width=1, line_color=p["muted"])
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(dtick=2)
    if unit == "R$":
        fig.update_yaxes(tickprefix="R$ ", rangemode="tozero")
    else:
        fig.update_yaxes(ticksuffix="%")
        fig.add_hline(y=0, line_width=1, line_color=p["axis"])
    return style(fig, height=430, legend=len(series) > 1)


def uf_map(df: pd.DataFrame, geojson: dict, col: str, label: str, unit: str, decimals: int,
           diverging: bool = False) -> go.Figure:
    """Mapa por UF (código IBGE em cod_uf)."""
    p = palette()
    z = df[col]
    if diverging:
        lim = float(z.abs().max())
        scale, zmin, zmax, zmid = diverging_scale(), -lim, lim, 0
    else:
        scale = [[i / (len(SEQUENTIAL) - 1), c] for i, c in enumerate(SEQUENTIAL)]
        zmin, zmax, zmid = float(z.min()), float(z.max()), None
    fig = go.Figure(go.Choropleth(
        geojson=geojson, featureidkey="properties.codarea", locations=df["cod_uf"].astype(str), z=z,
        colorscale=scale, zmin=zmin, zmax=zmax, zmid=zmid,
        marker_line_color=p["surface"], marker_line_width=1,
        customdata=[[u, value(v, unit, decimals), n] for u, v, n in zip(df["uf"], z, df["n"])],
        hovertemplate="%{customdata[0]}: %{customdata[1]}<br>%{customdata[2]} municípios<extra></extra>",
        colorbar=dict(title=dict(text=label, side="right"), thickness=10, outlinewidth=0,
                      tickfont_color=p["muted"], len=0.8,
                      ticksuffix="%" if unit == "%" else "", tickprefix="R$ " if unit == "R$" else ""),
    ))
    # Recorte fixo no Brasil continental: com fitbounds o quadro mantém a proporção 2:1 do
    # mundo e o país fica com metade da altura disponível. Ilhas oceânicas ficam de fora.
    fig.update_geos(lonaxis_range=[-74.5, -34.3], lataxis_range=[-34.2, 5.6], visible=False,
                    bgcolor="rgba(0,0,0,0)")
    fig = style(fig, height=520, legend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def histogram(values: pd.Series, modal: ModalClass, mean: float, median: float, unit: str,
              decimals: int, bins: int = 40) -> go.Figure:
    """Distribuição do ano: barras finas até o percentil 99, a classe modal de Sturges em
    faixa azul e média, mediana e moda marcadas.

    As classes de Sturges (usadas no cálculo da moda) são largas demais para enxergar o
    formato da distribuição, então o desenho usa faixas mais finas.
    """
    p = palette()
    lo, hi = float(values.min()), float(values.quantile(0.99))
    shown = values[values <= hi]
    edges = [lo + i * (hi - lo) / bins for i in range(bins + 1)]
    counts = pd.cut(shown, edges, include_lowest=True).value_counts(sort=False).to_numpy()
    fig = go.Figure()
    fig.add_vrect(x0=modal.inferior, x1=min(modal.superior, hi), fillcolor=p["series"][0], opacity=0.12,
                  line_width=0, layer="below")
    fig.add_annotation(x=(modal.inferior + min(modal.superior, hi)) / 2, y=1, yref="paper", yanchor="bottom",
                       text="classe modal (Sturges)", showarrow=False, font=dict(size=11, color=p["series"][0]))
    fig.add_trace(go.Bar(
        x=[(a + b) / 2 for a, b in zip(edges, edges[1:])], y=counts, width=(hi - lo) / bins * 0.92,
        marker_color=p["other"], marker_cornerradius=2,
        customdata=[f"{value(a, unit, decimals)} a {value(b, unit, decimals)}" for a, b in zip(edges, edges[1:])],
        hovertemplate="%{customdata}: %{y} municípios<extra></extra>",
    ))
    marks = [(modal.czuber, "moda", p["series"][0], 0.92),
             (median, "mediana", p["series"][1], 0.80),
             (mean, "média", p["ink"], 0.68)]
    for x, label, color, y in marks:
        fig.add_vline(x=x, line_width=2, line_color=color)
        fig.add_annotation(x=x, y=y, yref="paper", text=f"{label}: {value(x, unit, decimals)}", showarrow=False,
                           xanchor="left", xshift=4, font=dict(size=11, color=color), bgcolor=p["surface"])
    fig.update_xaxes(tickprefix="R$ " if unit == "R$" else "", ticksuffix="%" if unit == "%" else "")
    fig.update_yaxes(title=dict(text="municípios", font=dict(size=11)))
    return style(fig, height=380, legend=False)
