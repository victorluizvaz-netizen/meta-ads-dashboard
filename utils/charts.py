import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

BLUE   = "#4ADE80"
GREEN  = "#10B981"
RED    = "#EF4444"
ORANGE = "#F59E0B"
PURPLE = "#A78BFA"
CYAN   = "#06B6D4"
GRAY   = "#475569"

PALETTE = [BLUE, CYAN, ORANGE, PURPLE, GREEN, RED, GRAY]

_BG   = "rgba(0,0,0,0)"
_TEXT = "#5A7A5A"
_GRID = "#162016"

BASE = dict(
    plot_bgcolor=_BG,
    paper_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color=_TEXT),
    margin=dict(l=12, r=12, t=48, b=12),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#111A11",
        bordercolor="rgba(74,222,128,0.25)",
        font_color="#ECFDF5",
        font_size=12,
        font_family="Inter, sans-serif",
    ),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=11, color=_TEXT),
        bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(
        showgrid=False,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(size=11, color=_TEXT),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=_GRID,
        gridwidth=1,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(size=11, color=_TEXT),
        zeroline=False,
    ),
)


def _apply(fig, title):
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=13, color="#C4E8C4", family="Inter, sans-serif"),
            x=0,
            pad=dict(l=4),
        ),
        **BASE,
    )
    return fig


def line(df, x, y, title, label="", color=BLUE, prev_df=None, prev_label="Período anterior"):
    fig = go.Figure()
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    if prev_df is not None and not prev_df.empty and y in prev_df.columns:
        fig.add_trace(go.Scatter(
            x=prev_df[x], y=prev_df[y], name=prev_label,
            mode="lines",
            line=dict(color=GRAY, width=1.5, dash="dot", shape="spline", smoothing=0.8),
            opacity=0.4,
        ))

    fig.add_trace(go.Scatter(
        x=df[x], y=df[y], name=label or y,
        mode="lines",
        line=dict(color=color, width=2.5, shape="spline", smoothing=0.8),
        fill="tozeroy",
        fillgradient=dict(
            colorscale=[[0, f"rgba({r},{g},{b},0.0)"], [1, f"rgba({r},{g},{b},0.22)"]],
            type="vertical",
        ),
    ))
    return _apply(fig, title)


def multiline(df, x, cols, title):
    fig = go.Figure()
    for i, (col, label) in enumerate(cols):
        c = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=label,
            mode="lines",
            line=dict(color=c, width=2, shape="spline", smoothing=0.8),
        ))
    return _apply(fig, title)


def bar(df, x, y, title, color=BLUE, horizontal=False):
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    n = max(len(df) - 1, 1)

    if horizontal:
        fig = go.Figure(go.Bar(
            x=df[y], y=df[x], orientation="h",
            marker=dict(
                color=[f"rgba({r},{g},{b},{0.45 + 0.55*(i/n)})" for i in range(len(df))],
                line=dict(width=0),
                cornerradius=4,
            ),
        ))
        layout = {
            **BASE,
            "yaxis": dict(
                autorange="reversed",
                gridcolor=_GRID,
                tickfont=dict(size=11, color=_TEXT),
                linecolor="rgba(0,0,0,0)",
                zeroline=False,
            ),
            "xaxis": dict(showgrid=True, gridcolor=_GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11, color=_TEXT), zeroline=False),
        }
        fig.update_layout(title=dict(text=title, font=dict(size=13, color="#C4E8C4"), x=0, pad=dict(l=4)), **layout)
    else:
        fig = go.Figure(go.Bar(
            x=df[x], y=df[y],
            marker=dict(
                color=f"rgba({r},{g},{b},0.80)",
                line=dict(width=0),
                cornerradius=4,
            ),
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13, color="#C4E8C4"), x=0, pad=dict(l=4)),
            xaxis_tickangle=-35,
            **BASE,
        )
    return fig


def donut(labels, values, title):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.65,
        marker=dict(colors=PALETTE, line=dict(color="#0B0D0B", width=3)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#C4E8C4", family="Inter, sans-serif"),
        hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
        pull=[0.02] + [0] * (len(labels) - 1),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#C4E8C4"), x=0, pad=dict(l=4)),
        legend=dict(font=dict(size=11, color=_TEXT), bgcolor="rgba(0,0,0,0)"),
        **{k: v for k, v in BASE.items() if k not in ("legend",)},
    )
    return fig


def bar_compare(categories, values_current, values_prev, title, label_current="Período atual", label_prev="Período anterior"):
    fig = go.Figure()
    fig.add_trace(go.Bar(name=label_prev, x=categories, y=values_prev,
        marker=dict(color=GRAY, opacity=0.5, cornerradius=4, line=dict(width=0))))
    fig.add_trace(go.Bar(name=label_current, x=categories, y=values_current,
        marker=dict(color=BLUE, cornerradius=4, line=dict(width=0))))
    fig.update_layout(barmode="group", title=dict(text=title, font=dict(size=13, color="#C4E8C4"), x=0, pad=dict(l=4)), **BASE)
    return fig


def bar_with_avg(df, x, y, title, color=GREEN, avg_label="Média"):
    vals = df[y][df[y] > 0]
    avg = vals.mean() if not vals.empty else None
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    n = max(len(df) - 1, 1)
    fig = go.Figure(go.Bar(
        x=df[y], y=df[x], orientation="h",
        marker=dict(
            color=[f"rgba({r},{g},{b},{0.45 + 0.55*(i/n)})" for i in range(len(df))],
            line=dict(width=0),
            cornerradius=4,
        ),
    ))
    if avg is not None:
        f_str = f"{avg:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        fig.add_vline(
            x=avg, line_dash="dot", line_color=ORANGE,
            annotation_text=f"{avg_label}: R$ {f_str}",
            annotation_position="top right",
            annotation_font=dict(color=ORANGE, size=11),
        )
    layout = {
        **BASE,
        "yaxis": dict(autorange="reversed", gridcolor=_GRID, tickfont=dict(size=11, color=_TEXT), linecolor="rgba(0,0,0,0)", zeroline=False),
        "xaxis": dict(showgrid=True, gridcolor=_GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11, color=_TEXT), zeroline=False),
    }
    fig.update_layout(title=dict(text=title, font=dict(size=13, color="#C4E8C4"), x=0, pad=dict(l=4)), **layout)
    return fig


def bar_freq(df, x, y, title):
    def _color(v):
        if v >= 4.0: return RED
        if v >= 3.0: return ORANGE
        return BLUE
    colors = [_color(v) for v in df[y]]
    fig = go.Figure(go.Bar(
        x=df[y], y=df[x], orientation="h",
        marker=dict(color=colors, line=dict(width=0), cornerradius=4),
    ))
    fig.add_vline(x=3, line_dash="dot", line_color=ORANGE,
        annotation_text="⚠️ 3x", annotation_position="top",
        annotation_font=dict(color=ORANGE, size=11))
    fig.add_vline(x=4, line_dash="dot", line_color=RED,
        annotation_text="🔴 4x", annotation_position="top",
        annotation_font=dict(color=RED, size=11))
    layout = {
        **BASE,
        "yaxis": dict(autorange="reversed", gridcolor=_GRID, tickfont=dict(size=11, color=_TEXT), linecolor="rgba(0,0,0,0)", zeroline=False),
        "xaxis": dict(showgrid=True, gridcolor=_GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11, color=_TEXT), zeroline=False),
    }
    fig.update_layout(title=dict(text=title, font=dict(size=13, color="#C4E8C4"), x=0, pad=dict(l=4)), **layout)
    return fig
