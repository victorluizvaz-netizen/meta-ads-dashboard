import streamlit as st
from datetime import datetime, timedelta
from utils.meta_api import get_ad_accounts, get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils.alerts import generate_alerts
from utils import charts
from utils.styles import css, insight_box, section_header

st.set_page_config(page_title="Meta Ads Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.markdown(css(), unsafe_allow_html=True)

# ── Sidebar: conta e período ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Meta Ads")
    st.divider()

    with st.spinner("Carregando contas..."):
        try:
            accounts = get_ad_accounts()
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            st.stop()

    if not accounts:
        st.error("Nenhuma conta encontrada.")
        st.stop()

    account_options = {f"{a['name']}": a["id"] for a in accounts}
    selected_label = st.selectbox("Conta de anúncios", list(account_options.keys()))
    account_id = account_options[selected_label]
    st.divider()

    st.caption("Período de análise")
    since = st.date_input("De", value=datetime.today() - timedelta(days=29))
    until = st.date_input("Até", value=datetime.today() - timedelta(days=1))
    n_days = (until - since).days + 1
    st.caption(f"📅 {n_days} dias | comparando com {n_days} dias anteriores")

st.session_state["account_id"] = account_id
st.session_state["since"] = str(since)
st.session_state["until"] = str(until)

# ── Dados (carrega antes do filtro para popular as opções) ─────────────────────
with st.spinner("Buscando dados..."):
    try:
        df_raw, df_prev_raw, prev_since, prev_until = get_insights_with_comparison(account_id, str(since), str(until))
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        st.stop()

if df_raw.empty:
    st.warning("Nenhum dado encontrado. Tente um período diferente ou verifique a conta selecionada.")
    st.stop()

for _col in ("conversations",):
    if _col not in df_raw.columns:
        df_raw[_col] = 0
    if not df_prev_raw.empty and _col not in df_prev_raw.columns:
        df_prev_raw[_col] = 0

# ── Sidebar: filtro de campanhas ───────────────────────────────────────────────
all_campaigns = sorted(df_raw["campaign_name"].unique().tolist())

with st.sidebar:
    st.divider()
    st.caption("Filtro de campanhas")

    # Preserva seleção prévia se ainda válida para a conta/período atual
    prev_sel = [c for c in st.session_state.get("selected_campaigns", []) if c in all_campaigns]

    selected_campaigns = st.multiselect(
        "campanhas",
        options=all_campaigns,
        default=prev_sel,
        placeholder=f"Todas ({len(all_campaigns)})",
        label_visibility="collapsed",
    )

    if selected_campaigns:
        st.caption(f"🎯 {len(selected_campaigns)} de {len(all_campaigns)} selecionadas")
    else:
        st.caption(f"📋 {len(all_campaigns)} campanhas")

    st.divider()
    st.caption("Token válido por 60 dias.")

st.session_state["selected_campaigns"] = selected_campaigns

# ── Aplica filtro em memória ───────────────────────────────────────────────────
if selected_campaigns:
    df = df_raw[df_raw["campaign_name"].isin(selected_campaigns)].copy()
    df_prev = df_prev_raw[df_prev_raw["campaign_name"].isin(selected_campaigns)].copy() if not df_prev_raw.empty else df_prev_raw
else:
    df = df_raw.copy()
    df_prev = df_prev_raw.copy()

if df.empty:
    st.warning("Nenhum dado para as campanhas selecionadas. Ajuste o filtro ou o período.")
    st.stop()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Visão Geral")
st.caption(
    f"{since.strftime('%d/%m/%Y')} → {until.strftime('%d/%m/%Y')}"
    f"  ·  {df['campaign_name'].nunique()} campanhas"
    f"  ·  {df['campaign_type'].nunique()} tipos"
)

insight = top_insight(df, df_prev)
st.markdown(insight_box(insight), unsafe_allow_html=True)

# ── Alertas e sugestões ─────────────────────────────────────────────────────────
alerts = generate_alerts(df, df_prev)
if alerts:
    n_crit = sum(1 for a in alerts if a["level"] == "critical")
    n_warn = sum(1 for a in alerts if a["level"] == "warning")
    n_pos  = sum(1 for a in alerts if a["level"] == "positive")
    parts  = [f"⚡ {len(alerts)} alertas e sugestões"]
    if n_crit: parts.append(f"🔴 {n_crit} crítico{'s' if n_crit > 1 else ''}")
    if n_warn: parts.append(f"🟡 {n_warn} atenção")
    if n_pos:  parts.append(f"🟢 {n_pos} oportunidade{'s' if n_pos > 1 else ''}")

    _level_style = {
        "critical": ("rgba(239,68,68,0.1)",    "#FCA5A5", "rgba(239,68,68,0.3)"),
        "warning":  ("rgba(245,158,11,0.1)",   "#FCD34D", "rgba(245,158,11,0.3)"),
        "positive": ("rgba(16,185,129,0.1)",   "#6EE7B7", "rgba(16,185,129,0.3)"),
        "info":     ("rgba(99,179,237,0.1)",   "#90CDF4", "rgba(99,179,237,0.3)"),
    }
    _level_icon = {"critical": "🔴", "warning": "🟡", "positive": "🟢", "info": "🔵"}

    with st.expander(" · ".join(parts), expanded=n_crit > 0):
        for a in alerts:
            bg, fg, border = _level_style.get(a["level"], ("rgba(255,255,255,0.05)", "#F1F5F9", "rgba(255,255,255,0.1)"))
            icon = _level_icon.get(a["level"], "⚪")
            st.markdown(
                f'<div style="background:{bg};border:1px solid {border};border-radius:10px;'
                f'padding:0.65rem 1rem;margin:0.3rem 0;">'
                f'<b style="color:{fg};">{icon} [{a["category"]}] {a["title"]}</b><br>'
                f'<span style="color:#94A3B8;font-size:0.87rem;">{a["message"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── KPIs ───────────────────────────────────────────────────────────────────────
def metric(label, fmt_val, col_name, agg="sum", lower_is_better=False):
    cur = df[col_name].sum() if agg == "sum" else df[col_name].mean()
    prv_val = (
        df_prev[col_name].sum() if (not df_prev.empty and col_name in df_prev.columns and agg == "sum")
        else (df_prev[col_name].mean() if (not df_prev.empty and col_name in df_prev.columns) else 0)
    )
    d, pos = delta_pct(cur, prv_val)
    if lower_is_better and pos is not None:
        pos = not pos
    return label, fmt_val(cur), d, "normal" if (pos is None or pos) else "inverse"


c1, c2, c3, c4, c5 = st.columns(5)
for col_st, row in zip(
    [c1, c2, c3, c4, c5],
    [
        metric("💰 Investimento", currency, "spend"),
        metric("👁️ Impressões", number, "impressions"),
        metric("📣 Alcance", number, "reach"),
        metric("🖱️ Cliques", number, "clicks"),
        metric("📊 CTR Médio", percent, "ctr", agg="mean"),
    ],
):
    col_st.metric(row[0], row[1], delta=row[2], delta_color=row[3])

c6, c7, c8, c9, c10 = st.columns(5)
for col_st, row in zip(
    [c6, c7, c8, c9, c10],
    [
        metric("🎯 Leads", number, "leads"),
        metric("🛒 Compras", number, "purchases"),
        metric("💵 Receita", currency, "purchase_value"),
        metric("💸 CPM", currency, "cpm", agg="mean", lower_is_better=True),
        metric("🔁 ROAS", lambda x: f"{x:.2f}x", "roas", agg="mean"),
    ],
):
    col_st.metric(row[0], row[1], delta=row[2], delta_color=row[3])

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = (
    df.groupby("date")
    .agg(spend=("spend", "sum"), impressions=("impressions", "sum"), clicks=("clicks", "sum"))
    .reset_index()
)
daily_prev = df_prev.groupby("date").agg(spend=("spend", "sum")).reset_index() if not df_prev.empty else None

col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.line(daily, "date", "spend", "Investimento diário (R$)", "R$", prev_df=daily_prev),
        use_container_width=True,
    )
with col_b:
    by_type = df.groupby("campaign_type")["spend"].sum().reset_index()
    label_map = {
        "awareness": "Awareness", "traffic": "Tráfego",
        "leads": "Leads", "conversions": "Conversões", "other": "Outros",
    }
    by_type["campaign_type"] = by_type["campaign_type"].map(label_map).fillna("Outros")
    st.plotly_chart(
        charts.donut(by_type["campaign_type"].tolist(), by_type["spend"].tolist(), "Investimento por tipo de campanha"),
        use_container_width=True,
    )

col_c, col_d = st.columns(2)
with col_c:
    st.plotly_chart(
        charts.multiline(daily, "date", [("impressions", "Impressões"), ("clicks", "Cliques")], "Impressões vs Cliques"),
        use_container_width=True,
    )
with col_d:
    top10 = (
        df.groupby("campaign_name")["spend"].sum()
        .sort_values(ascending=False).head(10).reset_index()
    )
    top10.columns = ["Campanha", "Investimento"]
    st.plotly_chart(
        charts.bar(top10, "Campanha", "Investimento", "Top 10 campanhas por investimento", horizontal=True),
        use_container_width=True,
    )

st.divider()

# ── Tabela ─────────────────────────────────────────────────────────────────────
with st.expander("📋 Ver tabela completa de campanhas"):
    label_map2 = {
        "awareness": "Awareness", "traffic": "Tráfego",
        "leads": "Leads", "conversions": "Conversões", "other": "Outros",
    }
    summary = df.groupby(["campaign_name", "campaign_type"]).agg(
        Investimento=("spend", "sum"), Impressões=("impressions", "sum"),
        Alcance=("reach", "sum"), Cliques=("clicks", "sum"),
        Leads=("leads", "sum"), Conversas=("conversations", "sum"),
        Compras=("purchases", "sum"), Receita=("purchase_value", "sum"),
    ).reset_index()
    summary["ROAS"] = summary.apply(
        lambda r: r["Receita"] / r["Investimento"] if r["Investimento"] > 0 else 0, axis=1
    )
    summary["campaign_type"] = summary["campaign_type"].map(label_map2).fillna("Outros")
    summary = (
        summary.rename(columns={"campaign_name": "Campanha", "campaign_type": "Tipo"})
        .sort_values("Investimento", ascending=False)
    )
    st.dataframe(
        summary.style.format({
            "Investimento": lambda x: currency(x),
            "Impressões": lambda x: number(x),
            "Alcance": lambda x: number(x),
            "Cliques": lambda x: number(x),
            "Leads": lambda x: number(x),
            "Conversas": lambda x: number(x),
            "Compras": lambda x: number(x),
            "Receita": lambda x: currency(x),
            "ROAS": lambda x: f"{x:.2f}x",
        }),
        use_container_width=True,
        height=380,
    )
