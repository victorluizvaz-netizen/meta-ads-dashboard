import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

BLUE   = "#38BDF8"
GOLD   = "#F59E0B"
GREEN  = "#10B981"
RED    = "#EF4444"
ORANGE = "#F97316"
CYAN   = "#22D3EE"
GRAY   = "#4A7A9B"

PINK   = GOLD
PURPLE = "#0369A1"

PALETTE = [BLUE, GOLD, CYAN, GREEN, ORANGE, RED, GRAY]

_BG   = "rgba(0,0,0,0)"
_TEXT = "#4A7A9B"
_GRID = "#0A1428"

_TRANSITION = dict(duration=480, easing="cubic-in-out")


def _rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


BASE = dict(
    plot_bgcolor=_BG,
    paper_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color=_TEXT),
    margin=dict(l=12, r=12, t=52, b=12),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#050C1A",
        bordercolor="rgba(56,189,248,0.35)",
        font_color="#EFF6FF",
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
        gridcolor="rgba(10,20,40,0.8)",
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
            font=dict(size=13, color="#93C5FD", family="Inter, sans-serif"),
            x=0,
            pad=dict(l=4),
        ),
        transition=_TRANSITION,
        **BASE,
    )
    return fig


def line(df, x, y, title, label="", color=BLUE, prev_df=None, prev_label="Período anterior"):
    fig = go.Figure()
    r, g, b = _rgb(color)

    # Glow trace — linha mais larga e quase transparente para efeito halo
    if prev_df is not None and not prev_df.empty and y in prev_df.columns:
        fig.add_trace(go.Scatter(
            x=prev_df[x], y=prev_df[y], name=prev_label,
            mode="lines",
            line=dict(color=GRAY, width=1.5, dash="dot", shape="spline", smoothing=0.8),
            opacity=0.35,
            showlegend=True,
        ))

    # Halo/glow trace (sem legenda)
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y],
        mode="lines",
        line=dict(color=f"rgba({r},{g},{b},0.18)", width=12, shape="spline", smoothing=0.8),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Linha principal com fill gradiente
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y], name=label or y,
        mode="lines+markers",
        line=dict(color=color, width=2.5, shape="spline", smoothing=0.8),
        marker=dict(
            color=color,
            size=6,
            symbol="circle",
            line=dict(color=f"rgba({r},{g},{b},0.35)", width=3),
        ),
        fill="tozeroy",
        fillgradient=dict(
            colorscale=[
                [0, f"rgba({r},{g},{b},0.0)"],
                [1, f"rgba({r},{g},{b},0.22)"],
            ],
            type="vertical",
        ),
        hovertemplate="%{y}<extra></extra>",
    ))
    return _apply(fig, title)


def multiline(df, x, cols, title):
    fig = go.Figure()
    for i, (col, label) in enumerate(cols):
        c = PALETTE[i % len(PALETTE)]
        r, g, b = _rgb(c)
        # Halo
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col],
            mode="lines",
            line=dict(color=f"rgba({r},{g},{b},0.15)", width=10, shape="spline", smoothing=0.8),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=label,
            mode="lines+markers",
            line=dict(color=c, width=2.2, shape="spline", smoothing=0.8),
            marker=dict(color=c, size=5, line=dict(color=f"rgba({r},{g},{b},0.3)", width=2)),
            hovertemplate=f"{label}: %{{y}}<extra></extra>",
        ))
    return _apply(fig, title)


def _fmt_label(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.1f}k"
        return f"{v:,.0f}".replace(",", ".")
    return str(v)


def bar(df, x, y, title, color=BLUE, horizontal=False):
    r, g, b = _rgb(color)
    n = max(len(df) - 1, 1)
    colors = [f"rgba({r},{g},{b},{0.55 + 0.45*(i/n)})" for i in range(len(df))]

    if horizontal:
        labels = [_fmt_label(v) for v in df[y]]
        fig = go.Figure(go.Bar(
            x=df[y], y=df[x], orientation="h",
            marker=dict(color=colors, line=dict(width=0), cornerradius=6),
            text=labels,
            textposition="outside",
            textfont=dict(size=10, color="#7DD3FC"),
            cliponaxis=False,
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
            "xaxis": dict(
                showgrid=True, gridcolor=_GRID,
                linecolor="rgba(0,0,0,0)",
                tickfont=dict(size=11, color=_TEXT),
                zeroline=False,
            ),
        }
        fig.update_layout(
            title=dict(text=title, font=dict(size=13, color="#93C5FD"), x=0, pad=dict(l=4)),
            transition=_TRANSITION,
            **layout,
        )
    else:
        labels = [_fmt_label(v) for v in df[y]]
        fig = go.Figure(go.Bar(
            x=df[x], y=df[y],
            marker=dict(color=f"rgba({r},{g},{b},0.80)", line=dict(width=0), cornerradius=6),
            text=labels,
            textposition="outside",
            textfont=dict(size=10, color="#7DD3FC"),
            cliponaxis=False,
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13, color="#93C5FD"), x=0, pad=dict(l=4)),
            xaxis_tickangle=-35,
            transition=_TRANSITION,
            **BASE,
        )
    return fig


def donut(labels, values, title):
    palette = [BLUE, GOLD, CYAN, ORANGE, GREEN, RED, GRAY]
    total = sum(values) if values else 0
    if total >= 1_000_000:
        center_text = f"R$ {total/1_000_000:.1f}M"
    elif total >= 1_000:
        center_text = f"R$ {total/1_000:.1f}k"
    else:
        center_text = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.68,
        marker=dict(colors=palette, line=dict(color="#050C1A", width=3)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#93C5FD", family="Inter, sans-serif"),
        hovertemplate="%{label}: R$ %{value:,.2f} (%{percent})<extra></extra>",
        pull=[0.04] + [0] * (len(labels) - 1),
        rotation=90,
    ))
    fig.add_annotation(
        text=center_text,
        x=0.5, y=0.5,
        font=dict(size=15, color="#EFF6FF", family="Inter, sans-serif"),
        showarrow=False,
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#93C5FD"), x=0, pad=dict(l=4)),
        legend=dict(font=dict(size=11, color=_TEXT), bgcolor="rgba(0,0,0,0)"),
        transition=_TRANSITION,
        **{k: v for k, v in BASE.items() if k not in ("legend",)},
    )
    return fig


def bar_compare(categories, values_current, values_prev, title,
                label_current="Período atual", label_prev="Período anterior"):
    r, g, b = _rgb(BLUE)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=label_prev, x=categories, y=values_prev,
        marker=dict(color=GRAY, opacity=0.45, cornerradius=6, line=dict(width=0)),
        text=[_fmt_label(v) for v in values_prev],
        textposition="outside",
        textfont=dict(size=9, color=GRAY),
        cliponaxis=False,
    ))
    fig.add_trace(go.Bar(
        name=label_current, x=categories, y=values_current,
        marker=dict(color=f"rgba({r},{g},{b},0.85)", cornerradius=6, line=dict(width=0)),
        text=[_fmt_label(v) for v in values_current],
        textposition="outside",
        textfont=dict(size=9, color="#7DD3FC"),
        cliponaxis=False,
    ))
    fig.update_layout(
        barmode="group",
        title=dict(text=title, font=dict(size=13, color="#93C5FD"), x=0, pad=dict(l=4)),
        transition=_TRANSITION,
        **BASE,
    )
    return fig


def bar_with_avg(df, x, y, title, color=GREEN, avg_label="Média"):
    vals = df[y][df[y] > 0]
    avg  = vals.mean() if not vals.empty else None
    r, g, b = _rgb(color)
    n = max(len(df) - 1, 1)
    colors = [f"rgba({r},{g},{b},{0.50 + 0.50*(i/n)})" for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df[y], y=df[x], orientation="h",
        marker=dict(color=colors, line=dict(width=0), cornerradius=6),
        text=[_fmt_label(v) for v in df[y]],
        textposition="outside",
        textfont=dict(size=10, color=f"rgba({r},{g},{b},0.9)"),
        cliponaxis=False,
    ))
    if avg is not None:
        f_str = f"{avg:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        fig.add_vline(
            x=avg, line_dash="dot", line_color=ORANGE, line_width=1.5,
            annotation_text=f"{avg_label}: R$ {f_str}",
            annotation_position="top right",
            annotation_font=dict(color=ORANGE, size=11),
        )
    layout = {
        **BASE,
        "yaxis": dict(autorange="reversed", gridcolor=_GRID, tickfont=dict(size=11, color=_TEXT),
                      linecolor="rgba(0,0,0,0)", zeroline=False),
        "xaxis": dict(showgrid=True, gridcolor=_GRID, linecolor="rgba(0,0,0,0)",
                      tickfont=dict(size=11, color=_TEXT), zeroline=False),
    }
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#93C5FD"), x=0, pad=dict(l=4)),
        transition=_TRANSITION,
        **layout,
    )
    return fig


def bar_freq(df, x, y, title):
    def _color(v):
        if v >= 4.0: return RED
        if v >= 3.0: return ORANGE
        return BLUE
    colors = [_color(v) for v in df[y]]
    fig = go.Figure(go.Bar(
        x=df[y], y=df[x], orientation="h",
        marker=dict(color=colors, line=dict(width=0), cornerradius=6),
        text=[f"{v:.1f}x" for v in df[y]],
        textposition="outside",
        textfont=dict(size=10, color="#93C5FD"),
        cliponaxis=False,
    ))
    fig.add_vline(x=3, line_dash="dot", line_color=ORANGE, line_width=1.5,
        annotation_text="⚠ 3x", annotation_position="top",
        annotation_font=dict(color=ORANGE, size=11))
    fig.add_vline(x=4, line_dash="dot", line_color=RED, line_width=1.5,
        annotation_text="● 4x", annotation_position="top",
        annotation_font=dict(color=RED, size=11))
    layout = {
        **BASE,
        "yaxis": dict(autorange="reversed", gridcolor=_GRID, tickfont=dict(size=11, color=_TEXT),
                      linecolor="rgba(0,0,0,0)", zeroline=False),
        "xaxis": dict(showgrid=True, gridcolor=_GRID, linecolor="rgba(0,0,0,0)",
                      tickfont=dict(size=11, color=_TEXT), zeroline=False),
    }
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#93C5FD"), x=0, pad=dict(l=4)),
        transition=_TRANSITION,
        **layout,
    )
    return fig
