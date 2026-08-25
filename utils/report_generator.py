import base64
import math
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

# Paleta do relatório de CAMPANHA ÚNICA (utils/report_generator.py:generate_campaign_report_pdf,
# usada só por api/main.py:/api/campaign-report) — cores do Pulso, tema "Warp"
# (confirmadas em trello-clone/app/templates/base.html: prismic-violet/muted-cobalt e
# prismic-green/gold-leaf). O relatório de CONTA INTEIRA do Streamlit (generate_pdf_report,
# acima) mantém a paleta azul original — ninguém pediu pra mudar aquele, e são consumidores
# diferentes (agência olhando a conta toda vs. o botão do card de campanha no Pulso).
PULSO_BLUE    = "#6f839f"
PULSO_GOLD    = "#bd9f65"
PULSO_GREEN   = "#27AE60"
PULSO_RED     = "#e0736a"
PULSO_CAUTION = "#c98a4b"
PULSO_GRAY    = "#95A5A6"
PULSO_DONUT_COLORS = [PULSO_BLUE, PULSO_GOLD, PULSO_GREEN, PULSO_CAUTION, PULSO_RED, PULSO_GRAY]

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
    try:
        png = fig.to_image(format="png", width=880, height=340, scale=1.5)
        b64 = base64.b64encode(png).decode()
        return f'<div style="margin:8pt 0;"><img src="data:image/png;base64,{b64}" width="520" /></div>'
    except Exception:
        return '<p style="color:#95A5A6;font-size:9pt;font-style:italic;">[Gráfico não disponível neste ambiente]</p>'


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


def _creative_gallery_html(df):
    """Prévia visual dos anúncios (thumbnail + link de preview + link da Biblioteca de
    Anúncios da página). thumbnail_url/preview_link/library_link vêm de get_ad_creatives_bg
    (utils/meta_api_bg.py) — nem toda ad tem os três preenchidos (ex: ads antigas/pausadas)."""
    if df is None or df.empty or "thumbnail_url" not in df.columns:
        return ""
    cards = []
    for _, row in df.head(10).iterrows():
        thumb = row.get("thumbnail_url")
        img_html = (f'<img src="{thumb}" style="width:100%;height:110px;object-fit:cover;display:block;">'
                    if thumb else '<div style="width:100%;height:110px;background:#F0F2F5;"></div>')
        name = str(row.get("ad_name") or "")
        links = []
        if row.get("preview_link"):
            links.append(f'<a href="{row["preview_link"]}" target="_blank" rel="noopener" style="font-size:0.68rem;color:#1877F2;text-decoration:none;">Preview</a>')
        if row.get("library_link"):
            links.append(f'<a href="{row["library_link"]}" target="_blank" rel="noopener" style="font-size:0.68rem;color:#1877F2;text-decoration:none;">Biblioteca</a>')
        links_html = '<span style="color:#D1D5DB;"> &middot; </span>'.join(links) or '<span style="font-size:0.65rem;color:#95A5A6;">Sem link disponível</span>'
        cards.append(
            f'<div style="width:150px;background:white;border:1px solid #E4E6EB;border-radius:10px;overflow:hidden;">'
            f'{img_html}'
            f'<div style="padding:0.5rem;">'
            f'<p style="font-size:0.72rem;font-weight:600;color:#1C1E21;margin:0 0 0.35rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{name}">{name}</p>'
            f'<div>{links_html}</div>'
            f'</div></div>'
        )
    return f'<div style="display:flex;flex-wrap:wrap;gap:0.7rem;margin:0.7rem 0 1.1rem;">{"".join(cards)}</div>'


def _creative_gallery_pdf(df, cols=4):
    """Mesma prévia de _creative_gallery_html, em tabela (xhtml2pdf não suporta flexbox).
    Cartão com borda/fundo branco igual ao resto do relatório (_card_pdf) — sem isso a
    galeria destoava visualmente das outras seções (imagem soltando direto na página)."""
    if df is None or df.empty or "thumbnail_url" not in df.columns:
        return ""
    cells = []
    for _, row in df.head(10).iterrows():
        thumb = row.get("thumbnail_url")
        img_html = (
            f'<img src="{thumb}" width="110" height="110" style="border-radius:4pt;"/>' if thumb
            else '<table width="110" cellpadding="0" cellspacing="0"><tr><td height="110" '
                 'style="background-color:#F0F2F5;border-radius:4pt;">&nbsp;</td></tr></table>'
        )
        name = str(row.get("ad_name") or "")
        name = (name[:24] + "…") if len(name) > 24 else name
        links = []
        if row.get("preview_link"):
            links.append(f'<a href="{row["preview_link"]}" style="text-decoration:none;"><font color="#1877F2" size="1">Preview</font></a>')
        if row.get("library_link"):
            links.append(f'<a href="{row["library_link"]}" style="text-decoration:none;"><font color="#1877F2" size="1">Biblioteca</font></a>')
        links_html = ' <font color="#D1D5DB" size="1">&middot;</font> '.join(links) or '<font color="#95A5A6" size="1">Sem link disponível</font>'
        cells.append(
            f'<td width="{100 // cols}%" style="padding:5pt;vertical-align:top;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="background-color:white;'
            f'border:0.5pt solid #E4E6EB;border-radius:4pt;'
            f'page-break-inside:avoid;break-inside:avoid;">'
            f'<tr><td style="padding:10pt;text-align:center;">'
            f'{img_html}<br/><br/>'
            f'<font size="1" color="#1C1E21"><b>{name}</b></font><br/><br/>'
            f'{links_html}'
            f'</td></tr></table></td>'
        )
    rows_html = "".join(f'<tr>{"".join(cells[i:i + cols])}</tr>' for i in range(0, len(cells), cols))
    return f'<table width="100%" cellspacing="4" cellpadding="0" style="margin:6pt 0 10pt;">{rows_html}</table>'


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
        f'<div style="background-color:white;border:1pt solid #E4E6EB;padding:8pt 10pt;border-radius:4pt;">'
        f'<font size="1" color="#65676B"><b>{label.upper()}</b></font><br/>'
        f'<font size="3" color="#1C1E21"><b>{value}</b></font>{delta_html}</div>'
    )


def _row_pdf(card_tuples):
    """Flexbox, não tabela — testado direto contra o weasyprint real (mesmo motor
    do Railway): table-layout:fixed com <col width="%"> (o mesmo padrão que
    _campaign_table_pdf usa com sucesso pras tabelas) é ignorado aqui — a coluna
    cresce pro tamanho do conteúdo de qualquer jeito quando tem muitos cards numa
    linha só (ex: Conversões com "Conversas Iniciadas"/"Custo por Conversa"
    somados aos 5 já fixos vira 7), estourando a página. Flexbox com flex-wrap
    deixa os cards quebrarem pra uma segunda linha em vez de estourar — mesmo
    padrão já usado e comprovado na versão HTML (_row/_card)."""
    cols = "".join(
        f'<div style="flex:1 1 110pt;min-width:110pt;margin:2.5pt;">{_card_pdf(*t)}</div>'
        for t in card_tuples
    )
    return f'<div style="display:flex;flex-wrap:wrap;margin:8pt 0;">{cols}</div>'


def _section_pdf(title):
    return (
        f'<hr color="#1877F2" size="1"/>'
        f'<h2 style="font-size:12pt;color:#1C1E21;margin-top:12pt;margin-bottom:6pt;">{title}</h2>'
    )


# ── Template wrapper ───────────────────────────────────────────────────────────

def _wrap(body, client_name, since, until, for_pdf=False, cover=""):
    """cover: HTML de uma capa full-bleed (page-break-after:always), inserida ANTES
    do .wrapper com margem — só usada por generate_campaign_report_pdf. Quando
    presente, substitui o .header azul (a capa já mostra cliente/campanha/período)
    e a primeira página ganha margem zero (@page :first) pra capa ir até a borda.
    Parâmetro opcional com default "" — não muda nada pros callers existentes
    (generate_report/generate_pdf_report, relatório de conta inteira do Streamlit)."""
    font_import = "" if for_pdf else '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
    font_family = "Arial, sans-serif" if for_pdf else "'Inter', sans-serif"
    page_rules = '@page { margin: 1.5cm; size: A4; }' if for_pdf else ''
    if for_pdf and cover:
        page_rules += ' @page :first { margin: 0; }'
    header_html = "" if (for_pdf and cover) else f'''<div class="header">
    <h1>Relatório Meta Ads</h1>
    <p>Cliente: <b>{client_name}</b> &nbsp;|&nbsp; Período: <b>{since} → {until}</b></p>
  </div>'''
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
  {page_rules}
</style>
</head>
<body>
{cover}
<div class="wrapper">
  {header_html}
  {body}
  <div class="footer">Gerado automaticamente via Meta Ads Dashboard</div>
</div>
</body>
</html>"""


# ── Configuração dos conjuntos ────────────────────────────────────────────────

_OPT_RPT = {
    "REACH": "Alcance", "LINK_CLICKS": "Cliques no Link", "IMPRESSIONS": "Impressões",
    "LEAD_GENERATION": "Geração de Leads", "OFFSITE_CONVERSIONS": "Conversões",
    "LANDING_PAGE_VIEWS": "Pág. de Destino", "THRUPLAY": "ThruPlay",
    "APP_INSTALLS": "Instalações", "POST_ENGAGEMENT": "Engajamento",
    "CONVERSATIONS": "Conversas", "QUALITY_LEAD": "Leads Qualif.",
}
_BID_RPT = {
    "LOWEST_COST_WITHOUT_CAP": "Menor Custo",
    "LOWEST_COST_WITH_BID_CAP": "Lance Máximo",
    "COST_CAP": "Meta de Custo",
    "MINIMUM_ROAS": "ROAS Mínimo",
}
_PLAT_RPT = {"facebook": "FB", "instagram": "IG", "audience_network": "AN", "messenger": "Msg"}
_COUNTRY_RPT = {"BR": "Brasil", "US": "EUA", "AR": "Argentina", "PT": "Portugal",
                "CO": "Colômbia", "CL": "Chile", "MX": "México", "ES": "Espanha"}


def _cfg_summary(cfg: dict) -> dict:
    t = cfg.get("targeting") or {}
    genders = t.get("genders", [])
    if not genders or set(genders) >= {1, 2}:
        gender = "Todos"
    elif 1 in genders:
        gender = "Masculino"
    else:
        gender = "Feminino"
    geo = t.get("geo_locations", {})
    locs = [_COUNTRY_RPT.get(c, c) for c in geo.get("countries", [])]
    locs += [city.get("name", "") for city in geo.get("cities", [])]
    platforms = t.get("publisher_platforms", [])
    return {
        "name":      cfg.get("name", "—"),
        "opt_goal":  _OPT_RPT.get(cfg.get("optimization_goal", ""), cfg.get("optimization_goal", "") or "—"),
        "bid_strat": _BID_RPT.get(cfg.get("bid_strategy", ""), cfg.get("bid_strategy", "") or "—"),
        "age":       f"{t.get('age_min', 18)}–{t.get('age_max', 65)}",
        "gender":    gender,
        "locations": (", ".join(locs[:2]) + ("…" if len(locs) > 2 else "")) or "—",
        "platforms": ", ".join(_PLAT_RPT.get(p, p) for p in platforms) or "Auto",
    }


def _adset_config_table_html(adsets_config: list) -> str:
    if not adsets_config:
        return ""
    headers = ["Conjunto", "Otimização", "Lance", "Idade", "Gênero", "Localização", "Plataformas"]
    th = "".join(
        f'<th style="padding:7px 12px;text-align:{"left" if i==0 else "right"};font-size:0.7rem;'
        f'font-weight:700;color:#65676B;text-transform:uppercase;letter-spacing:0.05em;white-space:nowrap;">'
        f'{h}</th>'
        for i, h in enumerate(headers)
    )
    trs = ""
    for cfg in adsets_config:
        if "error" in cfg:
            continue
        s = _cfg_summary(cfg)
        vals = [s["name"], s["opt_goal"], s["bid_strat"], s["age"], s["gender"], s["locations"], s["platforms"]]
        cells = "".join(
            f'<td style="padding:7px 12px;text-align:{"left" if j==0 else "right"};font-size:0.82rem;'
            f'color:{"#1C1E21" if j==0 else "#444"};border-top:1px solid #F0F2F5;white-space:nowrap;">{v}</td>'
            for j, v in enumerate(vals)
        )
        trs += f'<tr>{cells}</tr>'
    if not trs:
        return ""
    return (
        '<p style="font-size:0.72rem;font-weight:700;color:#65676B;text-transform:uppercase;'
        'letter-spacing:0.06em;margin:1.2rem 0 0.4rem;">Configuração por conjunto</p>'
        '<div style="overflow-x:auto;margin-bottom:1.5rem;">'
        '<table style="width:100%;border-collapse:collapse;background:white;'
        'border:1px solid #E4E6EB;border-radius:10px;overflow:hidden;">'
        f'<thead><tr style="background:#F7F8FA;">{th}</tr></thead>'
        f'<tbody>{trs}</tbody>'
        '</table></div>'
    )


def _adset_config_table_pdf(adsets_config: list) -> str:
    if not adsets_config:
        return ""
    headers = ["Conjunto", "Otimização", "Lance", "Idade", "Gênero", "Localização", "Plats."]
    widths  = [22, 14, 13, 7, 9, 17, 10]
    cols_el = "".join(f'<col width="{w}%"/>' for w in widths)

    def td(content, idx, is_hdr=False):
        align  = "left" if idx == 0 else "right"
        bg     = "background-color:#F0F2F5;" if is_hdr else ""
        fw     = "font-weight:bold;" if is_hdr else ""
        border = "" if is_hdr else "border-top:0.5pt solid #E4E6EB;"
        return (f'<td style="{bg}{fw}{border}font-size:6pt;padding:2pt 3pt;'
                f'text-align:{align};word-wrap:break-word;">{content}</td>')

    hdr = "".join(td(h.upper(), i, True) for i, h in enumerate(headers))
    trs = ""
    for cfg in adsets_config:
        if "error" in cfg:
            continue
        s = _cfg_summary(cfg)
        name  = (s["name"][:28] + "…") if len(s["name"]) > 28 else s["name"]
        vals  = [name, s["opt_goal"], s["bid_strat"], s["age"], s["gender"], s["locations"], s["platforms"]]
        cells = "".join(td(v, i) for i, v in enumerate(vals))
        trs  += f'<tr>{cells}</tr>'
    if not trs:
        return ""
    return (
        '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:8pt;margin-bottom:2pt;">'
        'CONFIGURAÇÃO POR CONJUNTO</p>'
        f'<table width="100%" cellspacing="0" cellpadding="0" '
        f'style="margin-bottom:10pt;border:0.5pt solid #E4E6EB;table-layout:fixed;">'
        f'{cols_el}<tr>{hdr}</tr>{trs}</table>'
    )


# ── Builder HTML ───────────────────────────────────────────────────────────────

def _html_body(df, df_prev, sections, notes, chart_fn, df_adsets=None, df_ads=None, adsets_config=None):
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
            _as_layout = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5", automargin=True)}
            fig_as.update_layout(title="Top 10 conjuntos por investimento", **_as_layout)
            body += chart_fn(fig_as)
            body += _campaign_table_html(agg_as, cols_as)

    if "Criativos" in sections:
        result = _agg_ads(df_ads)
        if result[0] is not None:
            _, top_ctr, top_spend, base_cols = result
            body += _section("Criativos — Análise por Anúncio")
            body += _creative_gallery_html(top_spend)
            _cr_layout = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5", automargin=True)}

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

    if "Configuração dos Conjuntos" in sections and adsets_config:
        body += _section("Configuração dos Conjuntos de Anúncios")
        body += (
            '<p style="color:#65676B;font-size:0.85rem;margin-bottom:0.8rem;">'
            'Público-alvo, estratégia de lance e posicionamentos configurados por conjunto.</p>'
        )
        body += _adset_config_table_html(adsets_config)

    if notes.strip():
        body += _section("Observações")
        body += f'<p style="color:#1C1E21;line-height:1.7;white-space:pre-wrap;">{notes}</p>'

    return body


# ── Builder PDF ────────────────────────────────────────────────────────────────

def _pdf_body(df, df_prev, sections, notes, df_adsets=None, df_ads=None, adsets_config=None):
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
            _as_layout = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5", automargin=True)}
            fig_as.update_layout(title="Top 10 conjuntos por investimento", **_as_layout)
            body += _fig_png(fig_as)
            body += _campaign_table_pdf(agg_as, cols_as)

    if "Criativos" in sections:
        result = _agg_ads(df_ads)
        if result[0] is not None:
            _, top_ctr, top_spend, base_cols = result
            body += _section_pdf("Criativos — Análise por Anúncio")
            body += _creative_gallery_pdf(top_spend)
            _cr_layout_pdf = {**BASE_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#F0F2F5", automargin=True)}

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

    if "Configuração dos Conjuntos" in sections and adsets_config:
        body += _section_pdf("Configuração dos Conjuntos de Anúncios")
        body += _adset_config_table_pdf(adsets_config)

    if notes.strip():
        body += _section_pdf("Observações")
        body += f'<p style="font-size:9pt;line-height:1.6;">{notes}</p>'

    return body


# ── Relatório de campanha única (Pulso) — gráficos em SVG, sem Plotly/kaleido ──
#
# Caminho dedicado pro botão "Relatório da campanha" do Pulso (api/main.py:
# /api/campaign-report). Não usa go.Figure/_fig_png porque isso depende de
# kaleido, que nunca foi instalado na imagem da API no Railway — todo gráfico
# saía como "[Gráfico não disponível neste ambiente]" (confirmado gerando PDF
# real). Em vez de adicionar kaleido (pesado, e o pin do plotly==5.22.0 já está
# desalinhado até do lado Streamlit), os gráficos aqui são SVG puro, desenhado
# à mão — sem dependência externa, renderiza direto no weasyprint.

def _svg_line_chart(dates, series, width=520, height=200):
    """series: [(label, values, color) ou (label, values, color, 'dash'), ...].
    Preenche a área embaixo da primeira série (mesmo efeito visual do gráfico
    de investimento/receita atual)."""
    pad_l, pad_r, pad_t, pad_b = 4, 4, 6, 4
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(dates)
    all_vals = [v for _, vals, *_ in series for v in vals] or [0]
    vmax = (max(all_vals) or 1) * 1.15

    def xy(i, v):
        x = pad_l + (i / max(n - 1, 1)) * plot_w
        y = pad_t + plot_h - (v / vmax) * plot_h
        return x, y

    parts = [f'<line x1="{pad_l}" y1="{pad_t + plot_h:.1f}" x2="{width - pad_r}" y2="{pad_t + plot_h:.1f}" '
             f'stroke="#E4E6EB" stroke-width="1"/>']
    if series:
        label, values, color = series[0][0], series[0][1], series[0][2]
        pts = [xy(i, v) for i, v in enumerate(values)]
        if pts:
            area_d = (f"M {pts[0][0]:.1f},{pad_t + plot_h:.1f} "
                      + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                      + f" L {pts[-1][0]:.1f},{pad_t + plot_h:.1f} Z")
            parts.append(f'<path d="{area_d}" fill="{color}" fill-opacity="0.12"/>')
    for item in series:
        label, values, color = item[0], item[1], item[2]
        dashed = len(item) > 3 and item[3] == "dash"
        pts = [xy(i, v) for i, v in enumerate(values)]
        if not pts:
            continue
        path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        dash_attr = ' stroke-dasharray="5,3"' if dashed else ""
        parts.append(f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="2.2"{dash_attr} '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4pt;margin-right:12pt;">'
        f'<span style="display:inline-block;width:7pt;height:7pt;background:{c};border-radius:2pt;"></span>'
        f'<font size="1" color="#65676B">{lbl}</font></span>'
        for lbl, _, c, *_ in series
    )
    svg = (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')
    return f'<div style="margin:8pt 0 2pt;">{svg}</div><div style="margin-bottom:8pt;">{legend}</div>'


def _svg_bar_chart_v(dates, values, color, width=520, height=200):
    """Barras verticais por data (ex: leads por dia)."""
    pad_l, pad_r, pad_t, pad_b = 4, 4, 6, 4
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(values)
    vmax = (max(values) if values else 0) or 1
    vmax *= 1.15
    bar_w = (plot_w / max(n, 1)) * 0.6
    parts = [f'<line x1="{pad_l}" y1="{pad_t + plot_h:.1f}" x2="{width - pad_r}" y2="{pad_t + plot_h:.1f}" '
             f'stroke="#E4E6EB" stroke-width="1"/>']
    for i, v in enumerate(values):
        cx = pad_l + (i + 0.5) / max(n, 1) * plot_w
        h = (v / vmax) * plot_h if vmax else 0
        parts.append(f'<rect x="{cx - bar_w / 2:.1f}" y="{pad_t + plot_h - h:.1f}" width="{bar_w:.1f}" '
                     f'height="{h:.1f}" fill="{color}" rx="2"/>')
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _svg_bar_chart_h(items, width=520, row_h=22):
    """items: [(label, value, color, display_text), ...] — barras horizontais (ranking).
    display_text já vem formatado por quem chama (currency/percent/number conforme a
    métrica) — usar number() fixo aqui mostrava "0" pra CTR (0.85 arredondado)."""
    if not items:
        return ""
    label_w = 140
    val_w = 55
    bar_area = width - label_w - val_w
    vmax = max((v for _, v, _, _ in items), default=0) or 1
    height = row_h * len(items) + 6
    parts = []
    y = 3
    for label, value, color, display in items:
        bar_w = max((value / vmax) * bar_area, 2)
        lbl = (str(label)[:22] + "…") if len(str(label)) > 22 else str(label)
        parts.append(f'<text x="0" y="{y + row_h / 2 + 3:.1f}" font-size="8" fill="#1C1E21" '
                     f'font-family="Arial">{lbl}</text>')
        parts.append(f'<rect x="{label_w}" y="{y + 4}" width="{bar_w:.1f}" height="{row_h - 8}" '
                     f'fill="{color}" rx="2"/>')
        parts.append(f'<text x="{label_w + bar_w + 6:.1f}" y="{y + row_h / 2 + 3:.1f}" font-size="8" '
                     f'fill="#65676B" font-family="Arial">{display}</text>')
        y += row_h
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _polar(cx, cy, r, deg):
    rad = math.radians(deg - 90)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _donut_segment_path(cx, cy, r_outer, r_inner, start_deg, end_deg):
    large = 1 if (end_deg - start_deg) > 180 else 0
    x1o, y1o = _polar(cx, cy, r_outer, start_deg)
    x2o, y2o = _polar(cx, cy, r_outer, end_deg)
    x1i, y1i = _polar(cx, cy, r_inner, end_deg)
    x2i, y2i = _polar(cx, cy, r_inner, start_deg)
    return (f"M {x1o:.2f},{y1o:.2f} A {r_outer:.2f},{r_outer:.2f} 0 {large},1 {x2o:.2f},{y2o:.2f} "
            f"L {x1i:.2f},{y1i:.2f} A {r_inner:.2f},{r_inner:.2f} 0 {large},0 {x2i:.2f},{y2i:.2f} Z")


def _svg_donut_chart(segments, width=340, height=160):
    """segments: [(label, value, color), ...]. Rosca com legenda ao lado —
    proporção de investimento por conjunto de anúncios."""
    segments = [s for s in segments if s[1] > 0]
    if not segments:
        return ""
    total = sum(v for _, v, _ in segments)
    cx, cy, r_outer, r_inner = 62, height / 2, 52, 30
    if len(segments) == 1:
        color = segments[0][2]
        paths = [f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="{color}"/>',
                 f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="white"/>']
    else:
        paths = []
        angle = 0.0
        for _, value, color in segments:
            sweep = value / total * 360
            if sweep > 0:
                paths.append(f'<path d="{_donut_segment_path(cx, cy, r_outer, r_inner, angle, angle + sweep)}" '
                             f'fill="{color}"/>')
            angle += sweep
    legend = []
    ly = max(height / 2 - len(segments) * 9, 8)
    for label, value, color in segments[:8]:
        pct = value / total * 100
        lbl = (str(label)[:18] + "…") if len(str(label)) > 18 else str(label)
        legend.append(f'<rect x="130" y="{ly:.1f}" width="9" height="9" fill="{color}" rx="2"/>'
                      f'<text x="144" y="{ly + 8:.1f}" font-size="8" fill="#1C1E21" font-family="Arial">'
                      f'{lbl} ({pct:.0f}%)</text>')
        ly += 17
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(paths)}{"".join(legend)}</svg>')


def _icon_svg(path_or_shapes, color, size=18):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg" '
            f'style="flex-shrink:0;">{path_or_shapes.format(c=color)}</svg>')


_SECTION_ICON_SHAPES = {
    "overview":   '<rect x="3" y="10" width="3.5" height="7" fill="{c}"/><rect x="8.3" y="6" width="3.5" height="11" fill="{c}"/><rect x="13.5" y="2" width="3.5" height="15" fill="{c}"/>',
    "awareness":  '<circle cx="10" cy="10" r="8" fill="none" stroke="{c}" stroke-width="1.6"/><circle cx="10" cy="10" r="3" fill="{c}"/>',
    "traffic":    '<polygon points="4,3 4,17 8,13 11,19 13,18 10,12 16,12" fill="{c}"/>',
    "leads":      '<circle cx="10" cy="6" r="4" fill="{c}"/><path d="M2 19c0-4.5 3.5-7 8-7s8 2.5 8 7" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "conversions": '<circle cx="10" cy="10" r="9" fill="none" stroke="{c}" stroke-width="1.6"/><text x="10" y="14" font-size="11" font-weight="700" fill="{c}" text-anchor="middle" font-family="Arial">$</text>',
    "adsets":     '<rect x="3" y="3" width="14" height="4" rx="1.5" fill="{c}"/><rect x="3" y="9" width="14" height="4" rx="1.5" fill="{c}" opacity="0.7"/><rect x="3" y="15" width="14" height="4" rx="1.5" fill="{c}" opacity="0.45"/>',
    "creatives":  '<rect x="2" y="3" width="16" height="14" rx="2" fill="none" stroke="{c}" stroke-width="1.6"/><circle cx="7" cy="8" r="1.8" fill="{c}"/><path d="M3 15l4.5-5 3 3.5L15 9l3 6" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round" fill-opacity="0"/>',
}


def _section_campaign_pdf(icon_key, title):
    icon = _icon_svg(_SECTION_ICON_SHAPES.get(icon_key, ""), PULSO_BLUE) if icon_key in _SECTION_ICON_SHAPES else ""
    return (
        f'<div style="display:flex;align-items:center;gap:7pt;border-bottom:2pt solid {PULSO_BLUE};'
        f'margin-top:16pt;margin-bottom:8pt;padding-bottom:5pt;">'
        f'{icon}<h2 style="font-size:13pt;color:#1C1E21;">{title}</h2></div>'
    )


def _cover_pdf(client_name, campaign_name, since, until):
    return f'''<div style="page-break-after:always;position:relative;width:100%;height:29.7cm;">
  <div style="position:absolute;top:0;left:0;width:100%;height:60%;background:{PULSO_BLUE};"></div>
  <div style="position:absolute;top:0;right:0;width:9cm;height:60%;background:{PULSO_GOLD};"></div>
  <div style="position:absolute;top:9cm;left:1.6cm;color:white;">
    <p style="font-size:11pt;letter-spacing:3pt;text-transform:uppercase;color:#E8ECF1;margin-bottom:10pt;">Relatório de Campanha</p>
    <h1 style="font-size:28pt;font-weight:700;color:white;max-width:15cm;line-height:1.25;">{campaign_name}</h1>
    <p style="font-size:12pt;color:#E8ECF1;margin-top:8pt;">{client_name}</p>
  </div>
  <div style="position:absolute;bottom:3.2cm;left:1.6cm;color:#1C1E21;">
    <p style="font-size:9pt;color:#65676B;text-transform:uppercase;letter-spacing:1pt;">Período analisado</p>
    <p style="font-size:15pt;font-weight:700;">{since} — {until}</p>
  </div>
  <div style="position:absolute;bottom:1.3cm;left:1.6cm;font-size:9pt;color:#95A5A6;">Gerado automaticamente via Pulso</div>
</div>'''


def _campaign_pdf_body(df, sections, df_adsets=None, df_ads=None):
    """Mesma estrutura de seções que _pdf_body, mas sem comparação de período
    (o relatório de campanha única não tem período anterior) e com os
    componentes visuais do Pulso (_section_campaign_pdf, gráficos SVG)."""
    body = ""

    if "Visão Geral" in sections:
        body += _section_campaign_pdf("overview", "Visão Geral")
        body += _row_pdf([
            ("Investimento", currency(df["spend"].sum())),
            ("Impressões",   number(df["impressions"].sum())),
            ("Alcance",      number(df["reach"].sum())),
            ("Cliques",      number(df["clicks"].sum())),
        ])
        daily = df.groupby("date").agg(spend=("spend", "sum")).reset_index()
        body += _svg_line_chart(daily["date"].tolist(), [("Investimento (R$)", daily["spend"].tolist(), PULSO_BLUE)])
        body += _campaign_table_pdf(*_agg_overview(df))

    if "Awareness" in sections:
        dfa = df[df["campaign_type"] == "awareness"]
        if not dfa.empty:
            body += _section_campaign_pdf("awareness", "Awareness — Alcance e Visibilidade")
            freq = dfa["impressions"].sum() / dfa["reach"].sum() if dfa["reach"].sum() > 0 else 0
            body += _row_pdf([
                ("Alcance", number(dfa["reach"].sum())),
                ("Impressões", number(dfa["impressions"].sum())),
                ("Frequência", f"{freq:.2f}x"),
                ("CPM", currency(dfa["cpm"].mean())),
                ("Investimento", currency(dfa["spend"].sum())),
            ])
            daily_a = dfa.groupby("date").agg(reach=("reach", "sum"), impressions=("impressions", "sum")).reset_index()
            body += _svg_line_chart(daily_a["date"].tolist(), [
                ("Alcance", daily_a["reach"].tolist(), PULSO_BLUE),
                ("Impressões", daily_a["impressions"].tolist(), PULSO_GOLD),
            ])
            body += _campaign_table_pdf(*_agg_awareness(dfa))

    if "Tráfego" in sections:
        dft = df[df["campaign_type"] == "traffic"]
        if not dft.empty:
            body += _section_campaign_pdf("traffic", "Tráfego")
            ctr = dft["clicks"].sum() / dft["impressions"].sum() * 100 if dft["impressions"].sum() > 0 else 0
            body += _row_pdf([
                ("Cliques", number(dft["clicks"].sum())),
                ("Cliques no Link", number(dft["link_clicks"].sum())),
                ("CTR", percent(ctr)),
                ("CPC", currency(dft["cpc"].mean())),
                ("Investimento", currency(dft["spend"].sum())),
            ])
            daily_t = dft.groupby("date").agg(clicks=("clicks", "sum"), link_clicks=("link_clicks", "sum")).reset_index()
            body += _svg_line_chart(daily_t["date"].tolist(), [
                ("Cliques totais", daily_t["clicks"].tolist(), PULSO_BLUE),
                ("Cliques no link", daily_t["link_clicks"].tolist(), PULSO_GREEN),
            ])
            body += _campaign_table_pdf(*_agg_traffic(dft))

    if "Leads" in sections:
        dfl = df[df["campaign_type"] == "leads"]
        if not dfl.empty:
            body += _section_campaign_pdf("leads", "Geração de Leads")
            total_l = dfl["leads"].sum()
            spend_l = dfl["spend"].sum()
            cpl_val = spend_l / total_l if total_l > 0 else 0
            body += _row_pdf([
                ("Leads Gerados", number(total_l)),
                ("Custo por Lead", currency(cpl_val)),
                ("Investimento", currency(spend_l)),
                ("CTR", percent(dfl["ctr"].mean())),
            ])
            daily_l = dfl.groupby("date").agg(leads=("leads", "sum")).reset_index()
            body += _svg_bar_chart_v(daily_l["date"].tolist(), daily_l["leads"].tolist(), PULSO_GREEN)
            body += _campaign_table_pdf(*_agg_leads(dfl))

    if "Conversões" in sections:
        dfc, _, cd = _get_conv_data(df, pd.DataFrame())
        if not dfc.empty:
            body += _section_campaign_pdf("conversions", "Conversões e Vendas")
            cards = [
                ("Receita Gerada", currency(cd["total_rev"])),
                ("ROAS", roas(cd["roas_val"])),
                ("Compras", number(cd["total_pur"])),
                ("Custo por Compra", currency(cd["cpa_val"])),
                ("Investimento", currency(cd["total_spend_c"])),
            ]
            if cd["total_conv"] > 0:
                cards += [
                    ("Conversas Iniciadas", number(cd["total_conv"])),
                    ("Custo por Conversa", currency(cd["cpc_conv_val"])),
                ]
            body += _row_pdf(cards)
            daily_c = dfc.groupby("date").agg(purchase_value=("purchase_value", "sum"), spend=("spend", "sum")).reset_index()
            body += _svg_line_chart(daily_c["date"].tolist(), [
                ("Receita (R$)", daily_c["purchase_value"].tolist(), PULSO_GREEN),
                ("Investimento (R$)", daily_c["spend"].tolist(), PULSO_BLUE, "dash"),
            ])
            body += _campaign_table_pdf(*_agg_conversions(dfc))

    if "Conjuntos de Anúncios" in sections:
        agg_as, cols_as = _agg_adsets(df_adsets)
        if agg_as is not None:
            body += _section_campaign_pdf("adsets", "Conjuntos de Anúncios")
            top_as = agg_as.head(10)
            body += _svg_bar_chart_h([(r["adset_name"], r["spend"], PULSO_BLUE, currency(r["spend"])) for _, r in top_as.iterrows()])
            if len(top_as) > 1:
                segments = [(r["adset_name"], r["spend"], PULSO_DONUT_COLORS[i % len(PULSO_DONUT_COLORS)])
                           for i, (_, r) in enumerate(top_as.iterrows())]
                body += '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:6pt;margin-bottom:2pt;">DISTRIBUIÇÃO DO INVESTIMENTO</p>'
                body += _svg_donut_chart(segments)
            body += _campaign_table_pdf(agg_as, cols_as)

    if "Criativos" in sections:
        result = _agg_ads(df_ads)
        if result[0] is not None:
            _, top_ctr, top_spend, base_cols = result
            body += _section_campaign_pdf("creatives", "Criativos — Análise por Anúncio")
            body += _creative_gallery_pdf(top_spend)
            if not top_spend.empty:
                body += _svg_bar_chart_h([(r["ad_name"], r["spend"], PULSO_BLUE, currency(r["spend"])) for _, r in top_spend.iterrows()])
                body += '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:8pt;margin-bottom:2pt;">TOP 10 POR INVESTIMENTO</p>'
                body += _campaign_table_pdf(top_spend, base_cols)
            if not top_ctr.empty:
                body += _svg_bar_chart_h([(r["ad_name"], r["ctr"], PULSO_GOLD, percent(r["ctr"])) for _, r in top_ctr.iterrows()])
                body += '<p style="font-size:7pt;color:#65676B;font-weight:bold;margin-top:8pt;margin-bottom:2pt;">TOP 10 POR CTR</p>'
                body += _campaign_table_pdf(top_ctr, base_cols)

    return body


def generate_campaign_report_pdf(df, client_name, campaign_name, since, until, sections,
                                 df_adsets=None, df_ads=None) -> bytes:
    """Relatório em PDF de UMA campanha só, com a identidade visual do Pulso
    (capa, ícones, cores, gráficos em SVG) — usado por api/main.py:/api/campaign-report.
    Não reaproveita generate_pdf_report/_pdf_body de propósito: aquele caminho é
    usado pelo relatório de conta inteira do Streamlit e ninguém pediu pra mudar
    a aparência dele."""
    body = _campaign_pdf_body(df, sections, df_adsets=df_adsets, df_ads=df_ads)
    cover = _cover_pdf(client_name, campaign_name, since, until)
    html_str = _wrap(body, client_name, since, until, for_pdf=True, cover=cover)

    try:
        from weasyprint import HTML
        return HTML(string=html_str).write_pdf()
    except Exception:
        pass
    try:
        from xhtml2pdf import pisa
        buf = BytesIO()
        status = pisa.CreatePDF(html_str, dest=buf, encoding="utf-8")
        if not status.err:
            return buf.getvalue()
    except Exception:
        pass
    raise ImportError("pdf_unavailable")


# ── API pública ────────────────────────────────────────────────────────────────

def generate_report(df, df_prev, client_name, since, until, sections, notes="",
                    df_adsets=None, df_ads=None, adsets_config=None) -> str:
    first_flag = [True]
    body = _html_body(df, df_prev, sections, notes,
                      chart_fn=lambda fig: _fig_interactive(fig, first_flag),
                      df_adsets=df_adsets, df_ads=df_ads, adsets_config=adsets_config)
    return _wrap(body, client_name, since, until, for_pdf=False)


def generate_pdf_report(df, df_prev, client_name, since, until, sections, notes="",
                        df_adsets=None, df_ads=None, adsets_config=None) -> bytes:
    body     = _pdf_body(df, df_prev, sections, notes, df_adsets=df_adsets, df_ads=df_ads,
                         adsets_config=adsets_config)
    html_str = _wrap(body, client_name, since, until, for_pdf=True)

    # WeasyPrint — funciona no Linux (Cloud). Não requer GTK a partir da v60.
    try:
        from weasyprint import HTML
        return HTML(string=html_str).write_pdf()
    except Exception:
        pass

    # xhtml2pdf — funciona no Windows (local). Fallback se WeasyPrint indisponível.
    try:
        from xhtml2pdf import pisa
        buf = BytesIO()
        status = pisa.CreatePDF(html_str, dest=buf, encoding="utf-8")
        if not status.err:
            return buf.getvalue()
    except Exception:
        pass

    raise ImportError("pdf_unavailable")
