import streamlit as st
from datetime import datetime, timedelta
from utils.meta_api import get_ad_accounts, get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils.alerts import generate_alerts
from utils import charts
from utils.styles import css, insight_box, section_header, warning_box

st.set_page_config(page_title="Meta Ads Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.markdown(css(), unsafe_allow_html=True)

from utils.client_guard import redirect_if_client
redirect_if_client()

from utils.auth import require_login
require_login()

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
    st.caption(f"ID: `{account_id}`")
    st.divider()

    st.caption("Período de análise")
    since = st.date_input("De", value=datetime.today() - timedelta(days=29))
    until = st.date_input("Até", value=datetime.today() - timedelta(days=1))
    n_days = (until - since).days + 1

    comp_mode = st.selectbox(
        "Comparar com",
        options=["previous", "month", "year"],
        format_func=lambda x: {"previous": f"▸ {n_days} dias anteriores", "month": "▸ Mês anterior", "year": "▸ Mesmo período (ano anterior)"}[x],
        key="_comp_mode",
    )
    st.session_state["_comp_mode"] = comp_mode

st.session_state["account_id"] = account_id
st.session_state["since"] = str(since)
st.session_state["until"] = str(until)

# ── Dados ──────────────────────────────────────────────────────────────────────
with st.spinner("Buscando dados..."):
    try:
        df_raw, df_prev_raw, prev_since, prev_until = get_insights_with_comparison(account_id, str(since), str(until))
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        st.stop()

if df_raw.empty:
    st.warning("Nenhum dado encontrado. Tente um período diferente ou verifique a conta selecionada.")
    st.stop()

for _col in ("conversations", "cpc_conv"):
    if _col not in df_raw.columns:
        df_raw[_col] = 0
    if not df_prev_raw.empty and _col not in df_prev_raw.columns:
        df_prev_raw[_col] = 0

# ── Sidebar: filtro de campanhas ───────────────────────────────────────────────
all_campaigns = sorted(df_raw["campaign_name"].unique().tolist())

with st.sidebar:
    st.divider()
    st.caption("Filtro de campanhas")

    _CAMP_KEY = "_camp_ms"
    if _CAMP_KEY not in st.session_state:
        st.session_state[_CAMP_KEY] = [c for c in st.session_state.get("selected_campaigns", []) if c in all_campaigns]

    _ca, _cc = st.columns(2)
    if _ca.button("✓ Todas", key="btn_sel_all", use_container_width=True):
        st.session_state[_CAMP_KEY] = all_campaigns
        st.rerun()
    if _cc.button("✕ Limpar", key="btn_clr_sel", use_container_width=True):
        st.session_state[_CAMP_KEY] = []
        st.rerun()

    selected_campaigns = st.multiselect(
        "campanhas",
        options=all_campaigns,
        key=_CAMP_KEY,
        placeholder=f"Buscar campanha... ({len(all_campaigns)} no total)",
        label_visibility="collapsed",
    )

    if selected_campaigns:
        st.caption(f"🎯 {len(selected_campaigns)} de {len(all_campaigns)} selecionadas")
    else:
        st.caption(f"📋 Mostrando todas ({len(all_campaigns)})")

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
def ds(cur, prv, lower_is_better=False):
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    return d, "normal" if (pos is None or pos) else "inverse"

total_spend  = df["spend"].sum()
total_leads  = df["leads"].sum()
cpl          = total_spend / total_leads if total_leads > 0 else 0
total_conv   = df["conversations"].sum()
cpc_conv     = total_spend / total_conv if total_conv > 0 else 0
total_imp    = df["impressions"].sum()
total_reach  = df["reach"].sum()
total_clicks = df["clicks"].sum()
freq         = total_imp / total_reach if total_reach > 0 else 0
ctr          = total_clicks / total_imp * 100 if total_imp > 0 else 0
cpm          = total_spend / total_imp * 1000 if total_imp > 0 else 0
cpc          = total_spend / total_clicks if total_clicks > 0 else 0

prv_spend  = df_prev["spend"].sum() if not df_prev.empty else 0
prv_leads  = df_prev["leads"].sum() if not df_prev.empty else 0
prv_cpl    = prv_spend / prv_leads if prv_leads > 0 else 0
prv_conv   = df_prev["conversations"].sum() if not df_prev.empty else 0
prv_cpc_cv = prv_spend / prv_conv if prv_conv > 0 else 0
prv_imp    = df_prev["impressions"].sum() if not df_prev.empty else 0
prv_reach  = df_prev["reach"].sum() if not df_prev.empty else 0
prv_clicks = df_prev["clicks"].sum() if not df_prev.empty else 0
prv_ctr    = prv_clicks / prv_imp * 100 if prv_imp > 0 else 0
prv_cpm    = prv_spend / prv_imp * 1000 if prv_imp > 0 else 0
prv_cpc    = prv_spend / prv_clicks if prv_clicks > 0 else 0
prv_freq   = prv_imp / prv_reach if prv_reach > 0 else 0

# Linha 1: métricas de resultado
c1, c2, c3, c4, c5 = st.columns(5)
d, dc = ds(total_spend, prv_spend)
c1.metric("💰 Investimento", currency(total_spend), delta=d, delta_color=dc)
d, dc = ds(total_leads, prv_leads)
c2.metric("🎯 Leads", number(total_leads), delta=d, delta_color=dc)
d, dc = ds(cpl, prv_cpl, lower_is_better=True)
c3.metric("💸 CPL", currency(cpl) if total_leads > 0 else "—", delta=d if total_leads > 0 else None, delta_color=dc)
d, dc = ds(total_conv, prv_conv)
c4.metric("💬 Conversas", number(total_conv) if total_conv > 0 else "—", delta=d if total_conv > 0 else None, delta_color=dc)
d, dc = ds(cpc_conv, prv_cpc_cv, lower_is_better=True)
c5.metric("💬 Custo/Conversa", currency(cpc_conv) if total_conv > 0 else "—", delta=d if total_conv > 0 else None, delta_color=dc)

# Linha 2: métricas de eficiência
c6, c7, c8, c9 = st.columns(4)
d, dc = ds(ctr, prv_ctr)
c6.metric("📊 CTR médio", percent(ctr), delta=d, delta_color=dc)
d, dc = ds(cpm, prv_cpm, lower_is_better=True)
c7.metric("💸 CPM médio", currency(cpm), delta=d, delta_color=dc)
d, dc = ds(cpc, prv_cpc, lower_is_better=True)
c8.metric("🖱️ CPC médio", currency(cpc), delta=d, delta_color=dc)
freq_d, freq_dc = ds(freq, prv_freq, lower_is_better=True)
c9.metric("🔁 Frequência", f"{freq:.2f}x", delta=freq_d, delta_color=freq_dc)

# ROAS — apenas se houver dados de e-commerce
if df["purchase_value"].sum() > 0:
    roas_val  = df["purchase_value"].sum() / total_spend if total_spend > 0 else 0
    purchases = df["purchases"].sum()
    cpa_val   = total_spend / purchases if purchases > 0 else 0
    prv_rev   = df_prev["purchase_value"].sum() if not df_prev.empty else 0
    prv_pur   = df_prev["purchases"].sum() if not df_prev.empty else 0
    prv_roas  = prv_rev / prv_spend if prv_spend > 0 else 0
    prv_cpa   = prv_spend / prv_pur if prv_pur > 0 else 0
    with st.expander("📈 E-commerce / Vendas online (dados disponíveis)", expanded=False):
        rc1, rc2, rc3, rc4 = st.columns(4)
        d, dc = ds(df["purchase_value"].sum(), prv_rev)
        rc1.metric("💵 Receita", currency(df["purchase_value"].sum()), delta=d, delta_color=dc)
        d, dc = ds(roas_val, prv_roas)
        rc2.metric("🔁 ROAS", f"{roas_val:.2f}x", delta=d, delta_color=dc)
        d, dc = ds(purchases, prv_pur)
        rc3.metric("🛒 Compras", number(purchases), delta=d, delta_color=dc)
        d, dc = ds(cpa_val, prv_cpa, lower_is_better=True)
        rc4.metric("💸 CPA", currency(cpa_val), delta=d, delta_color=dc)

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = (
    df.groupby("date")
    .agg(spend=("spend", "sum"), leads=("leads", "sum"), impressions=("impressions", "sum"), clicks=("clicks", "sum"))
    .reset_index()
)
daily["cpm"] = daily.apply(lambda r: r["spend"] / r["impressions"] * 1000 if r["impressions"] > 0 else 0, axis=1)

daily_prev = (
    df_prev.groupby("date").agg(spend=("spend", "sum"), impressions=("impressions", "sum")).reset_index()
    if not df_prev.empty else None
)
if daily_prev is not None and not daily_prev.empty:
    daily_prev["cpm"] = daily_prev.apply(lambda r: r["spend"] / r["impressions"] * 1000 if r["impressions"] > 0 else 0, axis=1)

label_map = {"awareness": "Awareness", "traffic": "Tráfego", "leads": "Leads", "conversions": "Conversões", "other": "Outros"}

st.markdown(section_header("Custo & Distribuição", "investimento ao longo do tempo e por objetivo"), unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.line(daily, "date", "spend", "Investimento diário (R$)", "R$", prev_df=daily_prev),
        use_container_width=True,
    )
with col_b:
    by_type = df.groupby("campaign_type")["spend"].sum().reset_index()
    by_type["campaign_type"] = by_type["campaign_type"].map(label_map).fillna("Outros")
    st.plotly_chart(
        charts.donut(by_type["campaign_type"].tolist(), by_type["spend"].tolist(), "Investimento por tipo de campanha"),
        use_container_width=True,
    )

st.markdown(section_header("Eficiência de Clique & Custo por Lead", "performance por campanha"), unsafe_allow_html=True)
col_c, col_d = st.columns(2)
with col_c:
    ctr_camp = (
        df.groupby("campaign_name")
        .agg(clicks=("clicks", "sum"), impressions=("impressions", "sum"))
        .reset_index()
    )
    ctr_camp = ctr_camp[ctr_camp["impressions"] > 0].copy()
    ctr_camp["CTR (%)"] = ctr_camp["clicks"] / ctr_camp["impressions"] * 100
    ctr_camp = ctr_camp.sort_values("CTR (%)", ascending=False).head(10)
    ctr_camp = ctr_camp.rename(columns={"campaign_name": "Campanha"})
    st.plotly_chart(
        charts.bar(ctr_camp, "Campanha", "CTR (%)", "CTR por campanha (%)", color=charts.CYAN, horizontal=True),
        use_container_width=True,
    )
with col_d:
    dfl = df[df["campaign_type"] == "leads"]
    if not dfl.empty and dfl["leads"].sum() > 0:
        cpl_camp = dfl.groupby("campaign_name").agg(spend=("spend", "sum"), leads=("leads", "sum")).reset_index()
        cpl_camp = cpl_camp[cpl_camp["leads"] > 0].copy()
        cpl_camp["CPL (R$)"] = cpl_camp["spend"] / cpl_camp["leads"]
        cpl_camp = cpl_camp.sort_values("CPL (R$)").head(10)
        cpl_camp = cpl_camp.rename(columns={"campaign_name": "Campanha"})
        st.plotly_chart(
            charts.bar_with_avg(cpl_camp, "Campanha", "CPL (R$)", "CPL por campanha de leads (R$)", color=charts.GREEN),
            use_container_width=True,
        )
    else:
        top10 = (
            df.groupby("campaign_name")["spend"].sum()
            .sort_values(ascending=False).head(10).reset_index()
        )
        top10.columns = ["Campanha", "Investimento (R$)"]
        st.plotly_chart(
            charts.bar(top10, "Campanha", "Investimento (R$)", "Top 10 campanhas por investimento", horizontal=True),
            use_container_width=True,
        )

st.markdown(section_header("Leads & Frequência", "volume de leads e saturação de público"), unsafe_allow_html=True)
col_e, col_f = st.columns(2)
with col_e:
    daily_leads_prev = (
        df_prev.groupby("date").agg(leads=("leads", "sum")).reset_index()
        if not df_prev.empty else None
    )
    st.plotly_chart(
        charts.line(daily, "date", "leads", "Leads ao longo do tempo", "Leads", color=charts.GREEN,
                    prev_df=daily_leads_prev, prev_label="Leads período anterior"),
        use_container_width=True,
    )
with col_f:
    freq_camp = (
        df.groupby("campaign_name")
        .agg(impressions=("impressions", "sum"), reach=("reach", "sum"))
        .reset_index()
    )
    freq_camp = freq_camp[freq_camp["reach"] > 0].copy()
    freq_camp["Frequência"] = freq_camp["impressions"] / freq_camp["reach"]
    freq_camp = freq_camp.sort_values("Frequência", ascending=False).head(10)
    freq_camp = freq_camp.rename(columns={"campaign_name": "Campanha"})
    st.plotly_chart(
        charts.bar_freq(freq_camp, "Campanha", "Frequência", "Frequência por campanha"),
        use_container_width=True,
    )

st.markdown(section_header("CPM & Distribuição de Leads", "evolução de custo por impressão e ranking"), unsafe_allow_html=True)
col_g, col_h = st.columns(2)
with col_g:
    st.plotly_chart(
        charts.line(daily, "date", "cpm", "CPM ao longo do tempo (R$)", "R$", color=charts.PURPLE,
                    prev_df=daily_prev, prev_label="CPM período anterior"),
        use_container_width=True,
    )
with col_h:
    top5 = df.groupby("campaign_name")["leads"].sum().sort_values(ascending=False).head(5).reset_index()
    top5.columns = ["Campanha", "Leads"]
    st.plotly_chart(
        charts.bar(top5, "Campanha", "Leads", "Top 5 campanhas por leads", color=charts.GREEN, horizontal=True),
        use_container_width=True,
    )

st.divider()

# ── Tabela ─────────────────────────────────────────────────────────────────────
with st.expander("📋 Ver tabela completa de campanhas"):
    label_map2 = {"awareness": "Awareness", "traffic": "Tráfego", "leads": "Leads", "conversions": "Conversões", "other": "Outros"}
    summary = df.groupby(["campaign_name", "campaign_type"]).agg(
        Investimento=("spend", "sum"),
        Impressões=("impressions", "sum"),
        Alcance=("reach", "sum"),
        Cliques=("clicks", "sum"),
        Leads=("leads", "sum"),
        Conversas=("conversations", "sum"),
    ).reset_index()

    summary["CTR (%)"]    = summary.apply(lambda r: r["Cliques"] / r["Impressões"] * 100 if r["Impressões"] > 0 else 0, axis=1)
    summary["CPM (R$)"]   = summary.apply(lambda r: r["Investimento"] / r["Impressões"] * 1000 if r["Impressões"] > 0 else 0, axis=1)
    summary["CPC (R$)"]   = summary.apply(lambda r: r["Investimento"] / r["Cliques"] if r["Cliques"] > 0 else 0, axis=1)
    summary["CPL (R$)"]   = summary.apply(lambda r: r["Investimento"] / r["Leads"] if r["Leads"] > 0 else 0, axis=1)
    summary["Frequência"] = summary.apply(lambda r: r["Impressões"] / r["Alcance"] if r["Alcance"] > 0 else 0, axis=1)

    if not df_prev.empty:
        prev_agg = df_prev.groupby("campaign_name").agg(
            prev_spend=("spend", "sum"), prev_leads=("leads", "sum")
        ).reset_index()
        prev_agg["cpl_prev"] = prev_agg.apply(lambda r: r["prev_spend"] / r["prev_leads"] if r["prev_leads"] > 0 else 0, axis=1)
        summary = summary.merge(prev_agg[["campaign_name", "cpl_prev"]], on="campaign_name", how="left")
        summary["cpl_prev"] = summary["cpl_prev"].fillna(0)
        summary["Var. CPL"] = summary.apply(
            lambda r: f"{((r['CPL (R$)'] - r['cpl_prev']) / r['cpl_prev'] * 100):+.0f}%"
            if (r["cpl_prev"] > 0 and r["CPL (R$)"] > 0) else "—",
            axis=1,
        )
        summary = summary.drop(columns=["cpl_prev"])
    else:
        summary["Var. CPL"] = "—"

    summary["campaign_type"] = summary["campaign_type"].map(label_map2).fillna("Outros")
    summary = (
        summary.rename(columns={"campaign_name": "Campanha", "campaign_type": "Tipo"})
        .drop(columns=["Alcance"])
        .sort_values("Investimento", ascending=False)
    )
    st.dataframe(
        summary.style.format({
            "Investimento": lambda x: currency(x),
            "Impressões":   lambda x: number(x),
            "Cliques":      lambda x: number(x),
            "Leads":        lambda x: number(x),
            "Conversas":    lambda x: number(x),
            "CTR (%)":      lambda x: percent(x),
            "CPM (R$)":     lambda x: currency(x),
            "CPC (R$)":     lambda x: currency(x),
            "CPL (R$)":     lambda x: currency(x) if x > 0 else "—",
            "Frequência":   lambda x: f"{x:.2f}x",
        }),
        use_container_width=True,
        height=400,
    )
