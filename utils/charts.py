import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

BLUE   = "#6C63FF"
GREEN  = "#10B981"
RED    = "#EF4444"
ORANGE = "#F59E0B"
PURPLE = "#A78BFA"
CYAN   = "#06B6D4"
GRAY   = "#475569"

PALETTE = [BLUE, GREEN, ORANGE, PURPLE, CYAN, RED, GRAY]

_BG   = "rgba(0,0,0,0)"
_TEXT = "#94A3B8"
_GRID = "#1C2038"

BASE = dict(
    plot_bgcolor=_BG,
    paper_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color=_TEXT),
    margin=dict(l=10, r=10, t=45, b=10),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#1E2540", bordercolor="#2D3561", font_color="#F1F5F9"),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=11, color=_TEXT),
        bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(showgrid=False, linecolor=_GRID, tickfont=dict(size=11, color=_TEXT), zeroline=False),
    yaxis=dict(gridcolor=_GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11, color=_TEXT), zeroline=False),
)


def _apply(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, weight="bold", color="#E2E8F0"), x=0),
        **BASE,
    )
    return fig


def line(df, x, y, title, label="", color=BLUE, prev_df=None, prev_label="Período anterior"):
    fig = go.Figure()
    if prev_df is not None and not prev_df.empty and y in prev_df.columns:
        fig.add_trace(go.Scatter(
            x=prev_df[x], y=prev_df[y], name=prev_label,
            mode="lines", line=dict(color=GRAY, width=1.5, dash="dot"),
            opacity=0.5,
        ))
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y], name=label or y,
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=5, color=color, line=dict(width=1.5, color="#0D0F1C")),
        fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.08)",
    ))
    return _apply(fig, title)


def multiline(df, x, cols, title):
    fig = go.Figure()
    for i, (col, label) in enumerate(cols):
        c = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=label,
            mode="lines+markers",
            line=dict(color=c, width=2.5),
            marker=dict(size=5, color=c, line=dict(width=1.5, color="#0D0F1C")),
        ))
    return _apply(fig, title)


def bar(df, x, y, title, color=BLUE, horizontal=False):
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    if horizontal:
        fig = go.Figure(go.Bar(
            x=df[y], y=df[x], orientation="h",
            marker=dict(
                color=[f"rgba({r},{g},{b},{0.55 + 0.45*(i/max(len(df)-1,1))})" for i in range(len(df))],
                line=dict(width=0),
            ),
        ))
        layout = {
            **BASE,
            "yaxis": dict(autorange="reversed", gridcolor=_GRID, tickfont=dict(size=11, color=_TEXT), linecolor="rgba(0,0,0,0)", zeroline=False),
        }
        fig.update_layout(title=dict(text=title, font=dict(size=13, weight="bold", color="#E2E8F0"), x=0), **layout)
    else:
        fig = go.Figure(go.Bar(
            x=df[x], y=df[y],
            marker=dict(color=f"rgba({r},{g},{b},0.85)", line=dict(width=0)),
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13, weight="bold", color="#E2E8F0"), x=0),
            xaxis_tickangle=-35,
            **BASE,
        )
    return fig


def donut(labels, values, title):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=PALETTE, line=dict(color="#0D0F1C", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#E2E8F0"),
        hovertemplate="%{label}: %{value:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, weight="bold", color="#E2E8F0"), x=0),
        legend=dict(font=dict(size=11, color=_TEXT), bgcolor="rgba(0,0,0,0)"),
        **{k: v for k, v in BASE.items() if k not in ("legend",)},
    )
    return fig


def bar_compare(categories, values_current, values_prev, title, label_current="Período atual", label_prev="Período anterior"):
    fig = go.Figure()
    fig.add_trace(go.Bar(name=label_prev, x=categories, y=values_prev, marker_color=GRAY, opacity=0.6))
    fig.add_trace(go.Bar(name=label_current, x=categories, y=values_current, marker_color=BLUE))
    fig.update_layout(barmode="group", title=dict(text=title, font=dict(size=13, weight="bold", color="#E2E8F0"), x=0), **BASE)
    return fig
