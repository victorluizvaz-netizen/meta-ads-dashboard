import base64
from io import BytesIO
import pandas as pd
import plotly.graph_objects as go
from utils.formatters import currency, number, percent, roas, delta_pct
from utils.alerts import generate_alerts

PLOTLY_CDN = "cdn"  # deixa o Plotly escolher a versão correta do bundle JS

BLUE   = "#1877F2"
GREEN  = "#2ECC71"
ORANGE = "#F39C12"
PURPLE = "#9B59B6"
RED    = "#E74C3C"
GRAY   = "#95A5A6"
PALETTE = [BLUE, GREEN, ORANGE, PURPLE, RED, GRAY]

BASE_LAYOUT = dict(
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Arial, sans-serif", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
    hovermode="x unified",
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="#F0F2F5"),
    autosize=True,
    height=400,
)


# ── Dados compartilhados ───────────────────────────────────────────────────────

def _get_conv_data(df, df_prev):
    """Extrai métricas de conversões para HTML e PDF."""
    dfc   = df[df["campaign_type"] == "conversions"]
    dfc_p = df_prev[df_prev["campaign_type"] == "conversions"] if not df_prev.empty else pd.DataFrame()

    total_rev     = dfc["purchase_value"].sum()
    total_spend_c = dfc["spend"].sum()
    roas_val      = total_rev / total_spend_c if total_spend_c > 0 else 0
    total_pur     = dfc["purchases"].sum()
    cpa_val       = total_spend_c / total_pur if total_pur > 0 else 0
    total_conv    = dfc["conversations"].sum() if "conversations" in dfc.columns else 0
    cpc_conv_val  = total_spend_c / total_conv if total_conv > 0 else 0

    prev_rev      = dfc_p["purchase_value"].sum() if not dfc_p.empty else 0
    prev_spend_c  = dfc_p["spend"].sum() if not dfc_p.empty else 0
    prev_roas     = prev_rev / prev_spend_c if prev_spend_c > 0 else 0
    prev_pur      = dfc_p["purchases"].sum() if not dfc_p.empty else 0
    prev_conv     = dfc_p["conversations"].sum() if (not dfc_p.empty and "conversations" in dfc_p.columns) else 0
    prev_cpc_conv = prev_spend_c / prev_conv if prev_conv > 0 else 0

    return dfc, dfc_p, dict(
        total_rev=total_rev, total_spend_c=total_spend_c, roas_val=roas_val,
        total_pur=total_pur, cpa_val=cpa_val, total_conv=total_conv, cpc_conv_val=cpc_conv_val,
        prev_rev=prev_rev, prev_roas=prev_roas, prev_pur=prev_pur,
        prev_conv=prev_conv, prev_cpc_conv=prev_cpc_conv,
    )


# ── Gráficos ───────────────────────────────────────────────────────────────────

def _fig_interactive(fig, first_flag: list) -> str:
    include_js = first_flag[0]
    if include_js:
        first_flag[0] = False
    fig.update_layout(autosize=True)
    return '<div style="margin:1rem 0; width:100%; display:block;">' + fig.to_html(
        full_html=False,
        include_plotlyjs=PLOTLY_CDN if include_js else False,
        config={"displayModeBar": False, "responsive": True},
    ) + '</div>'


def _fig_png(fig) -> str:
    png = fig.to_image(format="png", width=880, height=340, scale=1.5)
    b64 = base64.b64encode(png).decode()
    return f'<div style="margin:8pt 0;"><img src="data:image/png;base64,{b64}" width="520" /></div>'


# ── Tabelas de detalhamento por campanha ───────────────────────────────────────

def _campaign_table_html(df_agg, col_configs):
    """Tabela HTML com métricas por campanha. col_configs: [(col, label, fmt_fn), ...]"""
    if df_agg is None or df_agg.empty:
        return ""
    th = "".join(
        f'<th style="padding:7px 12px;text-align:{"left" if i==0 else "right"};'
        f'font-size:0.7rem;font-weight:700;color:#65676B;text-transform:uppercase;'
        f'letter-spacing:0.05em;white-space:nowrap;">{label}</th>'
        for i, (_, label, _) in enumerate(col_configs)
    )
    trs = ""
    for _, row in df_agg.iterrows():
        tds = "".join(
            f'<td style="padding:7px 12px;text-align:{"left" if j==0 else "right"};'
            f'font-size:0.82rem;color:{"#1C1E21" if j==0 else "#444"};'
            f'border-top:1px solid #F0F2F5;white-space:nowrap;">'
            f'{fmt(row[col]) if col in row.index else "—"}</td>'
            for j, (col, _, fmt) in enumerate(col_configs)
        )
        trs += f'<tr>{tds}</tr>'
    return (
        '<p style="font-size:0.72rem;font-weight:700;color:#65676B;'
        'text-transform:uppercase;letter-spacing:0.06em;margin:1.2rem 0 0.4rem;">'
        'Detalhamento por campanha</p>'
        '<div style="overflow-x:auto;margin-bottom:1.5rem;">'
        '<table style="width:100%;border-collapse:collapse;background:white;'
        'border:1px solid #E4E6EB;border-radius:10px;overflow:hidden;">'
        f'<thead><tr style="background:#F7F8FA;">{th}</tr></thead>'
        f'<tbody>{trs}</tbody>'
        '</table></div>'
    )


def _campaign_table_pdf(df_agg, col_configs):
    """Tabela PDF com métricas por campanha."""
    if df_agg is None or df_agg.empty:
        return ""
    n = len(col_configs)
    text_count = sum(1 for _, _, fmt in col_configs if fmt is str)
    num_count  = n - text_count
    is_wide    = n > 6
    text_pct   = 22 if text_count > 1 else 32
    num_pct    = max(5, (100 - text_pct * text_count) // max(num_count, 1))
    font_size  = "6pt" if is_wide else "7pt"
    pad        = "2pt 3pt" if is_wide else "3pt 5pt"
    max_chars  = 25 if is_wide else 45

    col_widths = [text_pct if fmt is str else num_pct for _, _, fmt in col_configs]
    cols_el    = "".join(f'<col width="{w}%"/>' for w in col_widths)

    def _td(content, idx, is_hdr=False):
        align  = "left" if idx == 0 else "right"
        bg     = "background-color:#F0F2F5;" if is_hdr else ""
        fw     = "font-weight:bold;" if is_hdr else ""
        border = "" if is_hdr else "border-top:0.5pt solid #E4E6EB;"
        fs     = "6pt" if is_hdr else font_size
        return (f'<td style="{bg}{fw}{border}font-size:{fs};padding:{pad};'
                f'text-align:{align};width:{col_widths[idx]}%;word-wrap:break-word;">'
                f'{content}</td>')

    th  = "".join(_td(label.upper(), i, True) for i, (_, label, _) in enumerate(col_configs))
    trs = ""
    for _, row in df_agg.iterrows():
        cells = []
        for j, (col, _, fmt) in enumerate(col_configs):
            if col not in row.index:
                cells.append(_td("—", j))
                continue
            val = row[col]
            if fmt is str:
                s = str(val)
                display = (s[:max_chars] + "…") if len(s) > max_chars else s
            else:
                display = fmt(val)
            cells.append(_td(display, j))
        trs += f'<tr>{"".join(cells)}</tr>'

    return (
        '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:8pt;margin-bottom:2pt;">'
        'DETALHAMENTO POR CAMPANHA</p>'
        f'<table width="100%" cellspacing="0" cellpadding="0" '
        f'style="margin-bottom:10pt;border:0.5pt solid #E4E6EB;table-layout:fixed;">'
        f'{cols_el}'
        f'<tr>{th}</tr>{trs}</table>'
    )


def _agg_overview(df):
    g = df.groupby("campaign_name").agg(
        spend=("spend", "sum"), impressions=("impressions", "sum"),
        reach=("reach", "sum"), clicks=("clicks", "sum"),
    ).reset_index().sort_values("spend", ascending=False)
    return g, [
        ("campaign_name", "Campanha",    str),
        ("spend",         "Investimento", currency),
        ("impressions",   "Impressões",   number),
        ("reach",         "Alcance",      number),
        ("clicks",        "Cliques",      number),
    ]


def _agg_awareness(df):
    g = df.groupby("campaign_name").agg(
        reach=("reach", "sum"), impressions=("impressions", "sum"), spend=("spend", "sum"),
    ).reset_index().sort_values("spend", ascending=False)
    g["frequency"] = g.apply(lambda r: r["impressions"] / r["reach"] if r["reach"] > 0 else 0, axis=1)
    g["cpm"]       = g.apply(lambda r: r["spend"] / r["impressions"] * 1000 if r["impressions"] > 0 else 0, axis=1)
    return g, [
        ("campaign_name", "Campanha",    str),
        ("spend",         "Investimento", currency),
        ("reach",         "Alcance",     number),
        ("impressions",   "Impressões",  number),
        ("frequency",     "Frequência",  lambda v: f"{v:.2f}x"),
        ("cpm",           "CPM",         currency),
    ]


def _agg_traffic(df):
    g = df.groupby("campaign_name").agg(
        clicks=("clicks", "sum"), link_clicks=("link_clicks", "sum"),
        impressions=("impressions", "sum"), spend=("spend", "sum"),
    ).reset_index().sort_values("spend", ascending=False)
    g["ctr"] = g.apply(lambda r: r["clicks"] / r["impressions"] * 100 if r["impressions"] > 0 else 0, axis=1)
    g["cpc"] = g.apply(lambda r: r["spend"] / r["clicks"] if r["clicks"] > 0 else 0, axis=1)
    return g, [
        ("campaign_name", "Campanha",       str),
        ("spend",         "Investimento",   currency),
        ("clicks",        "Cliques",        number),
        ("link_clicks",   "Cliques no Link", number),
        ("ctr",           "CTR",            percent),
        ("cpc",           "CPC",            currency),
    ]


def _agg_leads(df):
    g = df.groupby("campaign_name").agg(
        leads=("leads", "sum"), spend=("spend", "sum"),
        impressions=("impressions", "sum"), clicks=("clicks", "sum"),
    ).reset_index().sort_values("spend", ascending=False)
    g["cpl"] = g.apply(lambda r: r["spend"] / r["leads"] if r["leads"] > 0 else 0, axis=1)
    g["ctr"] = g.apply(lambda r: r["clicks"] / r["impressions"] * 100 if r["impressions"] > 0 else 0, axis=1)
    return g, [
        ("campaign_name", "Campanha",      str),
        ("spend",         "Investimento",  currency),
        ("leads",         "Leads",         number),
        ("cpl",           "Custo por Lead", currency),
        ("ctr",           "CTR",           percent),
    ]


def _agg_conversions(df):
    df = df.copy()
    for col in ("conversations", "purchases", "purchase_value"):
        if col not in df.columns:
            df[col] = 0
    g = df.groupby("campaign_name").agg(
        spend=("spend", "sum"), purchase_value=("purchase_value", "sum"),
        purchases=("purchases", "sum"), conversations=("conversations", "sum"),
    ).reset_index().sort_values("spend", ascending=False)
    g["roas_v"] = g.apply(lambda r: r["purchase_value"] / r["spend"] if r["spend"] > 0 else 0, axis=1)
    g["cpa"]    = g.apply(lambda r: r["spend"] / r["purchases"] if r["purchases"] > 0 else 0, axis=1)
    cols = [
        ("campaign_name",  "Campanha",         str),
        ("spend",          "Investimento",      currency),
        ("purchase_value", "Receita",           currency),
        ("roas_v",         "ROAS",              roas),
        ("purchases",      "Compras",           number),
        ("cpa",            "Custo por Compra",  currency),
    ]
    if g["conversations"].sum() > 0:
        cols.append(("conversations", "Conversas", number))
    return g, cols


def _agg_ads(df_ads):
    if df_ads is None or df_ads.empty:
        return None, None, None
    df = df_ads.copy()
    df["roas_v"] = df.apply(lambda r: r["purchase_value"] / r["spend"] if r["spend"] > 0 else 0, axis=1)
    df["cpl_v"]  = df.apply(lambda r: r["spend"] / r["leads"]          if r["leads"]  > 0 else 0, axis=1)
    df["cpa_v"]  = df.apply(lambda r: r["spend"] / r["purchases"]      if r["purchases"] > 0 else 0, axis=1)

    base_cols = [
        ("ad_name",      "Anúncio",      str),
        ("adset_name",   "Conjunto",     str),
        ("spend",        "Investimento", currency),
        ("impressions",  "Impressões",   number),
        ("clicks",       "Cliques",      number),
        ("ctr",          "CTR",          percent),
        ("cpc",          "CPC",          currency),
        ("leads",        "Leads",        number),
        ("cpl_v",        "CPL",          currency),
        ("purchases",    "Compras",      number),
        ("roas_v",       "ROAS",         roas),
    ]

    # Top 10 por CTR (mínimo 200 impressões)
    top_ctr = df[df["impressions"] >= 200].sort_values("ctr", ascending=False).head(10)
    # Top 10 por investimento
    top_spend = df.sort_values("spend", ascending=False).head(10)

    return df, top_ctr, top_spend, base_cols


def _agg_adsets(df_adsets):
    if df_adsets is None or df_adsets.empty:
        return None, []
    agg = df_adsets.groupby("adset_name").agg(
        campaign_name=("campaign_name", "first"),
        spend=("spend", "sum"), impressions=("impressions", "sum"),
        clicks=("clicks", "sum"), leads=("leads", "sum"),
        purchases=("purchases", "sum"), purchase_value=("purchase_value", "sum"),
    ).reset_index()
    agg["ctr"]  = agg.apply(lambda r: r["clicks"] / r["impressions"] * 100 if r["impressions"] > 0 else 0, axis=1)
    agg["cpl"]  = agg.apply(lambda r: r["spend"]  / r["leads"]              if r["leads"]       > 0 else 0, axis=1)
    agg["roas_v"] = agg.apply(lambda r: r["purchase_value"] / r["spend"]    if r["spend"]       > 0 else 0, axis=1)
    agg = agg.sort_values("spend", ascending=False).head(15)
    cols = [
        ("adset_name",    "Conjunto",     str),
        ("campaign_name", "Campanha",     str),
        ("spend",         "Investimento", currency),
        ("impressions",   "Impressões",   number),
        ("clicks",        "Cliques",      number),
        ("ctr",           "CTR",          percent),
        ("leads",         "Leads",        number),
        ("cpl",           "CPL",          currency),
        ("purchases",     "Compras",      number),
        ("roas_v",        "ROAS",         roas),
    ]
    return agg, cols


# ── Alertas HTML ────────────────────────────────────────────────────────────────

def _alert_html(a):
    colors = {
        "critical": ("#FEF2F2", "#991B1B", "#FECACA"),
        "warning":  ("#FFFBEB", "#92400E", "#FDE68A"),
        "positive": ("#ECFDF5", "#065F46", "#A7F3D0"),
        "info":     ("#EFF6FF", "#1E40AF", "#BFDBFE"),
    }
    bg, text, border = colors.get(a["level"], ("#F9FAFB", "#374151", "#D1D5DB"))
    icon = {"critical": "🔴", "warning": "🟡", "positive": "🟢", "info": "🔵"}.get(a["level"], "⚪")
    return (
        f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
        f'padding:0.75rem 1rem;margin:0.45rem 0;">'
        f'<span style="font-weight:700;color:{text};">{icon}&nbsp;[{a["category"]}] {a["title"]}</span><br>'
        f'<span style="color:#374151;font-size:0.87rem;line-height:1.5;">{a["message"]}</span>'
        f'</div>'
    )


def _alert_pdf(a):
    colors = {
        "critical": ("#FEF2F2", "#991B1B"),
        "warning":  ("#FFFBEB", "#92400E"),
        "positive": ("#ECFDF5", "#065F46"),
        "info":     ("#EFF6FF", "#1E40AF"),
    }
    bg, text = colors.get(a["level"], ("#F9FAFB", "#374151"))
    badge = {"critical": "[CRÍTICO]", "warning": "[ATENÇÃO]", "positive": "[OPORTUNIDADE]", "info": "[INFO]"}.get(a["level"], "[-]")
    return (
        f'<table width="100%" cellspacing="0" style="background-color:{bg};'
        f'border:0.5pt solid #D1D5DB;margin-bottom:4pt;">'
        f'<tr><td style="padding:5pt 8pt;">'
        f'<font size="1" color="{text}"><b>{badge} [{a["category"]}] {a["title"]}</b></font><br/>'
        f'<font size="1" color="#374151">{a["message"]}</font>'
        f'</td></tr></table>'
    )


# ── Componentes HTML (flexbox) ─────────────────────────────────────────────────

def _card(label, value, delta_str=None, is_positive=None):
    delta_html = ""
    if delta_str:
        color = "#2ECC71" if is_positive else "#E74C3C"
        arrow = "▲" if is_positive else "▼"
        delta_html = f'<p style="margin:4px 0 0;font-size:0.78rem;color:{color};font-weight:600;">{arrow} {delta_str} vs período anterior</p>'
    return f"""<div style="background:white;border:1px solid #E4E6EB;border-radius:12px;padding:1.2rem 1.4rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
        <p style="margin:0;font-size:0.68rem;font-weight:700;color:#65676B;text-transform:uppercase;letter-spacing:0.07em;">{label}</p>
        <p style="margin:6px 0 0;font-size:1.5rem;font-weight:700;color:#1C1E21;">{value}</p>
        {delta_html}</div>"""


def _row(cards):
    cols = "".join(f'<div style="flex:1;min-width:150px;">{c}</div>' for c in cards)
    return f'<div style="display:flex;gap:0.8rem;flex-wrap:wrap;margin:1rem 0;">{cols}</div>'


def _section(title):
    return f'<h2 style="font-size:1.05rem;font-weight:700;color:#1C1E21;margin:2rem 0 1rem;padding-bottom:0.5rem;border-bottom:2px solid #1877F2;">{title}</h2>'


# ── Componentes PDF (tabelas — xhtml2pdf) ──────────────────────────────────────

def _card_pdf(label, value, delta_str=None, is_positive=None):
    delta_html = ""
    if delta_str:
        color = "#27AE60" if is_positive else "#C0392B"
        arrow = "▲" if is_positive else "▼"
        delta_html = f'<br/><font size="1" color="{color}"><b>{arrow} {delta_str} vs anterior</b></font>'
    return (
        f'<td style="background-color:white;border:1pt solid #E4E6EB;padding:8pt 10pt;border-radius:4pt;">'
        f'<font size="1" color="#65676B"><b>{label.upper()}</b></font><br/>'
        f'<font size="3" color="#1C1E21"><b>{value}</b></font>{delta_html}</td>'
    )


def _row_pdf(card_tuples):
    cells = "".join(_card_pdf(*t) for t in card_tuples)
    return f'<table width="100%" cellspacing="5" cellpadding="0" style="margin:8pt 0;"><tr>{cells}</tr></table>'


def _section_pdf(title):
    return (
        f'<hr color="#1877F2" size="1"/>'
        f'<h2 style="font-size:12pt;color:#1C1E21;margin-top:12pt;margin-bottom:6pt;">{title}</h2>'
    )


# ── Template wrapper ───────────────────────────────────────────────────────────

def _wrap(body, client_name, since, until, for_pdf=False):
    font_import = "" if for_pdf else '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
    font_family = "Arial, sans-serif" if for_pdf else "'Inter', sans-serif"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório Meta Ads — {client_name}</title>
{font_import}
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:{font_family}; background:#F7F8FA; color:#1C1E21; }}
  .wrapper {{ max-width:1100px; margin:0 auto; padding:{'1.5cm' if for_pdf else '2rem'}; }}
  .header {{ background:#1877F2; color:white; padding:{'1cm 1.5cm' if for_pdf else '2rem 2.5rem'};
             {'margin-bottom:1cm;' if for_pdf else 'margin-bottom:2rem;border-radius:16px;'} }}
  .header h1 {{ font-size:{'16pt' if for_pdf else '1.6rem'}; font-weight:700; margin-bottom:4pt; }}
  .header p  {{ font-size:{'9pt' if for_pdf else '0.9rem'}; opacity:0.9; }}
  .footer {{ text-align:center; color:#95A5A6; font-size:{'7pt' if for_pdf else '0.75rem'};
             margin-top:{'1cm' if for_pdf else '3rem'}; padding-top:8pt; border-top:1pt solid #E4E6EB; }}
  {'@page { margin: 1.5cm; size: A4; }' if for_pdf else ''}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>Relatório Meta Ads</h1>
    <p>Cliente: <b>{client_name}</b> &nbsp;|&nbsp; Período: <b>{since} → {until}</b></p>
  </div>
  {body}
  <div class="footer">Gerado automaticamente via Meta Ads Dashboard</div>
</div>
</body>
</html>"""


# ── Builder HTML ───────────────────────────────────────────────────────────────

def _html_body(df, df_prev, sections, notes, chart_fn, df_adsets=None, df_ads=None):
    body = ""

    def dp(col, agg="sum", lib=False):
        cur = df[col].sum() if agg == "sum" else df[col].mean()
        prv = (df_prev[col].sum() if (not df_prev.empty and col in df_prev.columns and agg == "sum")
               else (df_prev[col].mean() if (not df_prev.empty and col in df_prev.columns) else 0))
        d, pos = delta_pct(cur, prv)
        if lib and pos is not None:
            pos = not pos
        return d, pos

    if "Alertas e Sugestões" in sections:
        alerts = generate_alerts(df, df_prev, df_adsets=df_adsets)
        if alerts:
            body += _section("Alertas e Sugestões")
            n_crit = sum(1 for a in alerts if a["level"] == "critical")
            n_warn = sum(1 for a in alerts if a["level"] == "warning")
            n_pos  = sum(1 for a in alerts if a["level"] == "positive")
            summary = f"{len(alerts)} alertas"
            if n_crit: summary += f" · {n_crit} crítico(s)"
            if n_warn: summary += f" · {n_warn} atenção"
            if n_pos:  summary += f" · {n_pos} oportunidade(s)"
            body += f'<p style="color:#65676B;font-size:0.85rem;margin-bottom:0.8rem;">{summary}</p>'
            for a in alerts:
                body += _alert_html(a)

    if "Visão Geral" in sections:
        body += _section("Visão Geral")
        body += _row([
            _card("Investimento",  currency(df["spend"].sum()),      *dp("spend")),
            _card("Impressões",    number(df["impressions"].sum()),   *dp("impressions")),
            _card("Alcance",       number(df["reach"].sum()),         *dp("reach")),
            _card("Cliques",       number(df["clicks"].sum()),        *dp("clicks")),
        ])
        daily = df.groupby("date").agg(spend=("spend","sum")).reset_index()
        fig = go.Figure(go.Scatter(x=daily["date"], y=daily["spend"], name="Investimento",
                                   line=dict(color=BLUE, width=2.5), fill="tozeroy"))
        fig.update_layout(title="Investimento diário (R$)", **BASE_LAYOUT)
        body += chart_fn(fig)

        by_type = df.groupby("campaign_type")["spend"].sum().reset_index()
        fig2 = go.Figure(go.Pie(labels=by_type["campaign_type"], values=by_type["spend"],
                                hole=0.55, marker=dict(colors=PALETTE)))
        fig2.update_layout(title="Distribuição por tipo de campanha", **BASE_LAYOUT)
        body += chart_fn(fig2)
        body += _campaign_table_html(*_agg_overview(df))

    if "Awareness" in sections:
        dfa = df[df["campaign_type"] == "awareness"]
        if not dfa.empty:
            body += _section("Awareness — Alcance e Visibilidade")
            dfa_p = df_prev[df_prev["campaign_type"] == "awareness"] if not df_prev.empty else pd.DataFrame()
            d_reach, p_reach = delta_pct(dfa["reach"].sum(), dfa_p["reach"].sum() if not dfa_p.empty else 0)
            d_cpm, p_cpm_r   = delta_pct(dfa["cpm"].mean(),  dfa_p["cpm"].mean()  if not dfa_p.empty else 0)
            p_cpm = not p_cpm_r if p_cpm_r is not None else None
            freq  = dfa["impressions"].sum() / dfa["reach"].sum() if dfa["reach"].sum() > 0 else 0
            body += _row([
                _card("Alcance",      number(dfa["reach"].sum()),      d_reach, p_reach),
                _card("Impressões",   number(dfa["impressions"].sum())),
                _card("Frequência",   f"{freq:.2f}x"),
                _card("CPM",          currency(dfa["cpm"].mean()),     d_cpm,   p_cpm),
                _card("Investimento", currency(dfa["spend"].sum())),
            ])
            daily_a = dfa.groupby("date").agg(reach=("reach","sum"), impressions=("impressions","sum")).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_a["date"], y=daily_a["reach"],       name="Alcance",    line=dict(color=BLUE,   width=2.5)))
            fig.add_trace(go.Scatter(x=daily_a["date"], y=daily_a["impressions"], name="Impressões", line=dict(color=ORANGE, width=2)))
            fig.update_layout(title="Alcance e Impressões diárias", **BASE_LAYOUT)
            body += chart_fn(fig)
            body += _campaign_table_html(*_agg_awareness(dfa))

    if "Tráfego" in sections:
        dft = df[df["campaign_type"] == "traffic"]
        if not dft.empty:
            body += _section("Tráfego")
            dft_p = df_prev[df_prev["campaign_type"] == "traffic"] if not df_prev.empty else pd.DataFrame()
            d_cl, p_cl = delta_pct(dft["clicks"].sum(), dft_p["clicks"].sum() if not dft_p.empty else 0)
            d_cpc, p_cpc_r = delta_pct(dft["cpc"].mean(), dft_p["cpc"].mean() if not dft_p.empty else 0)
            p_cpc = not p_cpc_r if p_cpc_r is not None else None
            ctr = dft["clicks"].sum() / dft["impressions"].sum() * 100 if dft["impressions"].sum() > 0 else 0
            body += _row([
                _card("Cliques",         number(dft["clicks"].sum()),      d_cl,  p_cl),
                _card("Cliques no Link", number(dft["link_clicks"].sum())),
                _card("CTR",             percent(ctr)),
                _card("CPC",             currency(dft["cpc"].mean()),      d_cpc, p_cpc),
                _card("Investimento",    currency(dft["spend"].sum())),
            ])
            daily_t = dft.groupby("date").agg(clicks=("clicks","sum"), link_clicks=("link_clicks","sum")).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_t["date"], y=daily_t["clicks"],      name="Cliques totais",  line=dict(color=BLUE,  width=2.5)))
            fig.add_trace(go.Scatter(x=daily_t["date"], y=daily_t["link_clicks"], name="Cliques no link", line=dict(color=GREEN, width=2)))
            fig.update_layout(title="Cliques diários", **BASE_LAYOUT)
            body += chart_fn(fig)
            body += _campaign_table_html(*_agg_traffic(dft))

    if "Leads" in sections:
        dfl = df[df["campaign_type"] == "leads"]
        if not dfl.empty:
            body += _section("Geração de Leads")
            dfl_p = df_prev[df_prev["campaign_type"] == "leads"] if not df_prev.empty else pd.DataFrame()
            total_l  = dfl["leads"].sum();  spend_l = dfl["spend"].sum()
            cpl_val  = spend_l / total_l if total_l > 0 else 0
            prev_l   = dfl_p["leads"].sum() if not dfl_p.empty else 0
            prev_sl  = dfl_p["spend"].sum() if not dfl_p.empty else 0
            prev_cpl = prev_sl / prev_l if prev_l > 0 else 0
            d_l,   p_l   = delta_pct(total_l, prev_l)
            d_cpl, p_cpl_r = delta_pct(cpl_val, prev_cpl)
            p_cpl = not p_cpl_r if p_cpl_r is not None else None
            body += _row([
                _card("Leads Gerados",  number(total_l),  d_l,   p_l),
                _card("Custo por Lead", currency(cpl_val), d_cpl, p_cpl),
                _card("Investimento",   currency(spend_l)),
                _card("CTR",            percent(dfl["ctr"].mean())),
            ])
            daily_l = dfl.groupby("date").agg(leads=("leads","sum")).reset_index()
            fig = go.Figure(go.Bar(x=daily_l["date"], y=daily_l["leads"], name="Leads", marker_color=GREEN))
            fig.update_layout(title="Leads gerados por dia", **BASE_LAYOUT)
            body += chart_fn(fig)
            body += _campaign_table_html(*_agg_leads(dfl))

    if "Conversões" in sections:
        dfc, _, cd = _get_conv_data(df, df_prev)
        if not dfc.empty:
            body += _section("Conversões e Vendas")
            d_rev,  p_rev  = delta_pct(cd["total_rev"],    cd["prev_rev"])
            d_roas, p_roas = delta_pct(cd["roas_val"],     cd["prev_roas"])
            d_pur,  p_pur  = delta_pct(cd["total_pur"],    cd["prev_pur"])
            d_conv, p_conv = delta_pct(cd["total_conv"],   cd["prev_conv"])
            d_cpc_c, p_cpc_c_r = delta_pct(cd["cpc_conv_val"], cd["prev_cpc_conv"])
            p_cpc_c = not p_cpc_c_r if p_cpc_c_r is not None else None
            cards = [
                _card("Receita Gerada",   currency(cd["total_rev"]),   d_rev,  p_rev),
                _card("ROAS",             roas(cd["roas_val"]),         d_roas, p_roas),
                _card("Compras",          number(cd["total_pur"]),      d_pur,  p_pur),
                _card("Custo por Compra", currency(cd["cpa_val"])),
                _card("Investimento",     currency(cd["total_spend_c"])),
            ]
            if cd["total_conv"] > 0:
                cards += [
                    _card("Conversas Iniciadas", number(cd["total_conv"]),     d_conv,  p_conv),
                    _card("Custo por Conversa",  currency(cd["cpc_conv_val"]), d_cpc_c, p_cpc_c),
                ]
            body += _row(cards)
            daily_c = dfc.groupby("date").agg(purchase_value=("purchase_value","sum"), spend=("spend","sum")).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_c["date"], y=daily_c["purchase_value"], name="Receita (R$)",
                                     fill="tozeroy", line=dict(color=GREEN, width=2.5)))
            fig.add_trace(go.Scatter(x=daily_c["date"], y=daily_c["spend"], name="Investimento (R$)",
                                     line=dict(color=BLUE, width=2, dash="dot")))
            fig.update_layout(title="Receita vs Investimento", **BASE_LAYOUT)
            body += chart_fn(fig)
            body += _campaign_table_html(*_agg_conversions(dfc))

    if "Conjuntos de Anúncios" in sections:
        agg_as, cols_as = _agg_adsets(df_adsets)
        if agg_as is not None:
            body += _section("Conjuntos de Anúncios")
            top_as = agg_as.head(10)
            fig_as = go.Figure(go.Bar(
                x=top_as["spend"], y=top_as["adset_name"], orientation="h",
                marker=dict(color=BLUE),
            ))
            _as_layout = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5")}
            fig_as.update_layout(title="Top 10 conjuntos por investimento", **_as_layout)
            body += chart_fn(fig_as)
            body += _campaign_table_html(agg_as, cols_as)

    if "Criativos" in sections:
        result = _agg_ads(df_ads)
        if result[0] is not None:
            _, top_ctr, top_spend, base_cols = result
            body += _section("Criativos — Análise por Anúncio")
            _cr_layout = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5")}

            if not top_spend.empty:
                fig_cr = go.Figure(go.Bar(
                    x=top_spend["spend"], y=top_spend["ad_name"], orientation="h",
                    marker=dict(color=BLUE),
                ))
                fig_cr.update_layout(title="Top 10 anúncios por investimento", **_cr_layout)
                body += chart_fn(fig_cr)
                body += '<p style="font-size:0.72rem;font-weight:700;color:#65676B;text-transform:uppercase;letter-spacing:0.06em;margin:1.2rem 0 0.4rem;">Top 10 por investimento</p>'
                body += _campaign_table_html(top_spend, base_cols)

            if not top_ctr.empty:
                fig_ctr = go.Figure(go.Bar(
                    x=top_ctr["ctr"], y=top_ctr["ad_name"], orientation="h",
                    marker=dict(color=GREEN),
                ))
                fig_ctr.update_layout(title="Top 10 anúncios por CTR (%)", **_cr_layout)
                body += chart_fn(fig_ctr)
                body += '<p style="font-size:0.72rem;font-weight:700;color:#65676B;text-transform:uppercase;letter-spacing:0.06em;margin:1.2rem 0 0.4rem;">Top 10 por CTR</p>'
                body += _campaign_table_html(top_ctr, base_cols)

    if notes.strip():
        body += _section("Observações")
        body += f'<p style="color:#1C1E21;line-height:1.7;white-space:pre-wrap;">{notes}</p>'

    return body


# ── Builder PDF ────────────────────────────────────────────────────────────────

def _pdf_body(df, df_prev, sections, notes, df_adsets=None, df_ads=None):
    body = ""

    def dp2(col, src_df, prev_df, agg="sum", lib=False):
        cur = src_df[col].sum() if agg == "sum" else src_df[col].mean()
        prv = (prev_df[col].sum() if (not prev_df.empty and col in prev_df.columns and agg == "sum")
               else (prev_df[col].mean() if (not prev_df.empty and col in prev_df.columns) else 0))
        d, pos = delta_pct(cur, prv)
        if lib and pos is not None:
            pos = not pos
        return d, pos

    if "Alertas e Sugestões" in sections:
        alerts = generate_alerts(df, df_prev, df_adsets=df_adsets)
        if alerts:
            body += _section_pdf("Alertas e Sugestões")
            for a in alerts:
                body += _alert_pdf(a)

    if "Visão Geral" in sections:
        body += _section_pdf("Visão Geral")
        body += _row_pdf([
            ("Investimento",  currency(df["spend"].sum()),      *dp2("spend",       df, df_prev)),
            ("Impressões",    number(df["impressions"].sum()),   *dp2("impressions", df, df_prev)),
            ("Alcance",       number(df["reach"].sum()),         *dp2("reach",       df, df_prev)),
            ("Cliques",       number(df["clicks"].sum()),        *dp2("clicks",      df, df_prev)),
        ])
        daily = df.groupby("date").agg(spend=("spend","sum")).reset_index()
        fig = go.Figure(go.Scatter(x=daily["date"], y=daily["spend"], name="Investimento",
                                   line=dict(color=BLUE, width=2.5), fill="tozeroy"))
        fig.update_layout(title="Investimento diário (R$)", **BASE_LAYOUT)
        body += _fig_png(fig)
        body += _campaign_table_pdf(*_agg_overview(df))

    if "Awareness" in sections:
        dfa = df[df["campaign_type"] == "awareness"]
        if not dfa.empty:
            body += _section_pdf("Awareness — Alcance e Visibilidade")
            dfa_p = df_prev[df_prev["campaign_type"] == "awareness"] if not df_prev.empty else pd.DataFrame()
            d_reach, p_reach = delta_pct(dfa["reach"].sum(), dfa_p["reach"].sum() if not dfa_p.empty else 0)
            d_cpm, p_cpm_r   = delta_pct(dfa["cpm"].mean(),  dfa_p["cpm"].mean()  if not dfa_p.empty else 0)
            p_cpm = not p_cpm_r if p_cpm_r is not None else None
            freq  = dfa["impressions"].sum() / dfa["reach"].sum() if dfa["reach"].sum() > 0 else 0
            body += _row_pdf([
                ("Alcance",      number(dfa["reach"].sum()),      d_reach, p_reach),
                ("Impressões",   number(dfa["impressions"].sum())),
                ("Frequência",   f"{freq:.2f}x"),
                ("CPM",          currency(dfa["cpm"].mean()),     d_cpm,   p_cpm),
                ("Investimento", currency(dfa["spend"].sum())),
            ])
            daily_a = dfa.groupby("date").agg(reach=("reach","sum"), impressions=("impressions","sum")).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_a["date"], y=daily_a["reach"],       name="Alcance",    line=dict(color=BLUE,   width=2.5)))
            fig.add_trace(go.Scatter(x=daily_a["date"], y=daily_a["impressions"], name="Impressões", line=dict(color=ORANGE, width=2)))
            fig.update_layout(title="Alcance e Impressões diárias", **BASE_LAYOUT)
            body += _fig_png(fig)
            body += _campaign_table_pdf(*_agg_awareness(dfa))

    if "Tráfego" in sections:
        dft = df[df["campaign_type"] == "traffic"]
        if not dft.empty:
            body += _section_pdf("Tráfego")
            dft_p = df_prev[df_prev["campaign_type"] == "traffic"] if not df_prev.empty else pd.DataFrame()
            d_cl,  p_cl   = delta_pct(dft["clicks"].sum(), dft_p["clicks"].sum() if not dft_p.empty else 0)
            d_cpc, p_cpc_r = delta_pct(dft["cpc"].mean(),  dft_p["cpc"].mean()  if not dft_p.empty else 0)
            p_cpc = not p_cpc_r if p_cpc_r is not None else None
            ctr = dft["clicks"].sum() / dft["impressions"].sum() * 100 if dft["impressions"].sum() > 0 else 0
            body += _row_pdf([
                ("Cliques",         number(dft["clicks"].sum()),      d_cl,  p_cl),
                ("Cliques no Link", number(dft["link_clicks"].sum())),
                ("CTR",             percent(ctr)),
                ("CPC",             currency(dft["cpc"].mean()),      d_cpc, p_cpc),
                ("Investimento",    currency(dft["spend"].sum())),
            ])
            daily_t = dft.groupby("date").agg(clicks=("clicks","sum"), link_clicks=("link_clicks","sum")).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_t["date"], y=daily_t["clicks"],      name="Cliques totais",  line=dict(color=BLUE,  width=2.5)))
            fig.add_trace(go.Scatter(x=daily_t["date"], y=daily_t["link_clicks"], name="Cliques no link", line=dict(color=GREEN, width=2)))
            fig.update_layout(title="Cliques diários", **BASE_LAYOUT)
            body += _fig_png(fig)
            body += _campaign_table_pdf(*_agg_traffic(dft))

    if "Leads" in sections:
        dfl = df[df["campaign_type"] == "leads"]
        if not dfl.empty:
            body += _section_pdf("Geração de Leads")
            dfl_p = df_prev[df_prev["campaign_type"] == "leads"] if not df_prev.empty else pd.DataFrame()
            total_l  = dfl["leads"].sum();  spend_l = dfl["spend"].sum()
            cpl_val  = spend_l / total_l if total_l > 0 else 0
            prev_l   = dfl_p["leads"].sum() if not dfl_p.empty else 0
            prev_sl  = dfl_p["spend"].sum() if not dfl_p.empty else 0
            prev_cpl = prev_sl / prev_l if prev_l > 0 else 0
            d_l,   p_l   = delta_pct(total_l, prev_l)
            d_cpl, p_cpl_r = delta_pct(cpl_val, prev_cpl)
            p_cpl = not p_cpl_r if p_cpl_r is not None else None
            body += _row_pdf([
                ("Leads Gerados",  number(total_l),   d_l,   p_l),
                ("Custo por Lead", currency(cpl_val), d_cpl, p_cpl),
                ("Investimento",   currency(spend_l)),
                ("CTR",            percent(dfl["ctr"].mean())),
            ])
            daily_l = dfl.groupby("date").agg(leads=("leads","sum")).reset_index()
            fig = go.Figure(go.Bar(x=daily_l["date"], y=daily_l["leads"], name="Leads", marker_color=GREEN))
            fig.update_layout(title="Leads gerados por dia", **BASE_LAYOUT)
            body += _fig_png(fig)
            body += _campaign_table_pdf(*_agg_leads(dfl))

    if "Conversões" in sections:
        dfc, _, cd = _get_conv_data(df, df_prev)
        if not dfc.empty:
            body += _section_pdf("Conversões e Vendas")
            d_rev,  p_rev  = delta_pct(cd["total_rev"],    cd["prev_rev"])
            d_roas, p_roas = delta_pct(cd["roas_val"],     cd["prev_roas"])
            d_pur,  p_pur  = delta_pct(cd["total_pur"],    cd["prev_pur"])
            d_conv, p_conv = delta_pct(cd["total_conv"],   cd["prev_conv"])
            d_cpc_c, p_cpc_c_r = delta_pct(cd["cpc_conv_val"], cd["prev_cpc_conv"])
            p_cpc_c = not p_cpc_c_r if p_cpc_c_r is not None else None
            cards = [
                ("Receita Gerada",   currency(cd["total_rev"]),   d_rev,  p_rev),
                ("ROAS",             roas(cd["roas_val"]),         d_roas, p_roas),
                ("Compras",          number(cd["total_pur"]),      d_pur,  p_pur),
                ("Custo por Compra", currency(cd["cpa_val"])),
                ("Investimento",     currency(cd["total_spend_c"])),
            ]
            if cd["total_conv"] > 0:
                cards += [
                    ("Conversas Iniciadas", number(cd["total_conv"]),     d_conv,  p_conv),
                    ("Custo por Conversa",  currency(cd["cpc_conv_val"]), d_cpc_c, p_cpc_c),
                ]
            body += _row_pdf(cards)
            daily_c = dfc.groupby("date").agg(purchase_value=("purchase_value","sum"), spend=("spend","sum")).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_c["date"], y=daily_c["purchase_value"], name="Receita (R$)",
                                     fill="tozeroy", line=dict(color=GREEN, width=2.5)))
            fig.add_trace(go.Scatter(x=daily_c["date"], y=daily_c["spend"], name="Investimento (R$)",
                                     line=dict(color=BLUE, width=2, dash="dot")))
            fig.update_layout(title="Receita vs Investimento", **BASE_LAYOUT)
            body += _fig_png(fig)
            body += _campaign_table_pdf(*_agg_conversions(dfc))

    if "Conjuntos de Anúncios" in sections:
        agg_as, cols_as = _agg_adsets(df_adsets)
        if agg_as is not None:
            body += _section_pdf("Conjuntos de Anúncios")
            top_as = agg_as.head(10)
            fig_as = go.Figure(go.Bar(
                x=top_as["spend"], y=top_as["adset_name"], orientation="h",
                marker=dict(color=BLUE),
            ))
            _as_layout = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5")}
            fig_as.update_layout(title="Top 10 conjuntos por investimento", **_as_layout)
            body += _fig_png(fig_as)
            body += _campaign_table_pdf(agg_as, cols_as)

    if "Criativos" in sections:
        result = _agg_ads(df_ads)
        if result[0] is not None:
            _, top_ctr, top_spend, base_cols = result
            body += _section_pdf("Criativos — Análise por Anúncio")
            _cr_layout_pdf = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5")}

            if not top_spend.empty:
                fig_cr = go.Figure(go.Bar(
                    x=top_spend["spend"], y=top_spend["ad_name"], orientation="h",
                    marker=dict(color=BLUE),
                ))
                fig_cr.update_layout(title="Top 10 anúncios por investimento", **_cr_layout_pdf)
                body += _fig_png(fig_cr)
                body += '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:8pt;margin-bottom:2pt;">TOP 10 POR INVESTIMENTO</p>'
                body += _campaign_table_pdf(top_spend, base_cols)

            if not top_ctr.empty:
                fig_ctr = go.Figure(go.Bar(
                    x=top_ctr["ctr"], y=top_ctr["ad_name"], orientation="h",
                    marker=dict(color=GREEN),
                ))
                fig_ctr.update_layout(title="Top 10 anúncios por CTR (%)", **_cr_layout_pdf)
                body += _fig_png(fig_ctr)
                body += '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:8pt;margin-bottom:2pt;">TOP 10 POR CTR</p>'
                body += _campaign_table_pdf(top_ctr, base_cols)

    if notes.strip():
        body += _section_pdf("Observações")
        body += f'<p style="font-size:9pt;line-height:1.6;">{notes}</p>'

    return body


# ── API pública ────────────────────────────────────────────────────────────────

def generate_report(df, df_prev, client_name, since, until, sections, notes="", df_adsets=None, df_ads=None) -> str:
    first_flag = [True]
    body = _html_body(df, df_prev, sections, notes,
                      chart_fn=lambda fig: _fig_interactive(fig, first_flag),
                      df_adsets=df_adsets, df_ads=df_ads)
    return _wrap(body, client_name, since, until, for_pdf=False)


def generate_pdf_report(df, df_prev, client_name, since, until, sections, notes="", df_adsets=None, df_ads=None) -> bytes:
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise ImportError("pdf_unavailable")

    body = _pdf_body(df, df_prev, sections, notes, df_adsets=df_adsets, df_ads=df_ads)
    html = _wrap(body, client_name, since, until, for_pdf=True)

    buf = BytesIO()
    status = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if status.err:
        raise RuntimeError(f"xhtml2pdf: {status.err} erros ao gerar PDF")
    return buf.getvalue()
