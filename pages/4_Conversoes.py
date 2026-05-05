import streamlit as st
from utils.meta_api import get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils import charts
from utils.styles import css, insight_box

st.set_page_config(page_title="Conversões | Meta Ads", page_icon="🔄", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

account_id = st.session_state.get("account_id")
since = st.session_state.get("since")
until = st.session_state.get("until")

if not account_id:
    st.warning("⚠️ Volte à página principal e selecione uma conta.")
    st.stop()

with st.spinner("Carregando..."):
    try:
        df_all, df_prev_all, prev_since, prev_until = get_insights_with_comparison(account_id, since, until)
    except Exception as e:
        st.error(f"Erro: {e}")
        st.stop()

for _col in ("conversations", "cpc_conv"):
    if _col not in df_all.columns:
        df_all[_col] = 0
    if not df_prev_all.empty and _col not in df_prev_all.columns:
        df_prev_all[_col] = 0

selected = st.session_state.get("selected_campaigns", [])
if selected:
    df_all = df_all[df_all["campaign_name"].isin(selected)]
    if not df_prev_all.empty:
        df_prev_all = df_prev_all[df_prev_all["campaign_name"].isin(selected)]

df = df_all[df_all["campaign_type"] == "conversions"].copy()
df_prev = df_prev_all[df_prev_all["campaign_type"] == "conversions"].copy() if not df_prev_all.empty else df_prev_all

st.title("🔄 Conversões")
st.caption(f"Engajamento, conversas e aquisição  ·  {since} → {until}")

if df.empty:
    st.info("Nenhuma campanha de Conversões encontrada neste período.")
    st.stop()

st.markdown(insight_box(top_insight(df_all, df_prev_all, "conversions")), unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
def delta_show(cur, prv, lower_is_better=False):
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    return d, "normal" if (pos is None or pos) else "inverse"

spend        = df["spend"].sum()
conversations = df["conversations"].sum()
cpc_conv     = spend / conversations if conversations > 0 else 0
leads        = df["leads"].sum()
cpl          = spend / leads if leads > 0 else 0
clicks       = df["clicks"].sum()
impressions  = df["impressions"].sum()
ctr          = clicks / impressions * 100 if impressions > 0 else 0
cpm          = spend / impressions * 1000 if impressions > 0 else 0
cpc          = spend / clicks if clicks > 0 else 0

prv_spend   = df_prev["spend"].sum() if not df_prev.empty else 0
prv_conv    = df_prev["conversations"].sum() if not df_prev.empty else 0
prv_cpc_cv  = prv_spend / prv_conv if prv_conv > 0 else 0
prv_leads   = df_prev["leads"].sum() if not df_prev.empty else 0
prv_cpl     = prv_spend / prv_leads if prv_leads > 0 else 0
prv_clicks  = df_prev["clicks"].sum() if not df_prev.empty else 0
prv_imp     = df_prev["impressions"].sum() if not df_prev.empty else 0
prv_ctr     = prv_clicks / prv_imp * 100 if prv_imp > 0 else 0
prv_cpm     = prv_spend / prv_imp * 1000 if prv_imp > 0 else 0
prv_cpc     = prv_spend / prv_clicks if prv_clicks > 0 else 0

# Linha 1: resultado primário
c1, c2, c3, c4, c5 = st.columns(5)
d, dc = delta_show(spend, prv_spend)
c1.metric("💰 Investimento", currency(spend), delta=d, delta_color=dc)
d, dc = delta_show(conversations, prv_conv)
c2.metric("💬 Conversas iniciadas", number(conversations) if conversations > 0 else "—", delta=d if conversations > 0 else None, delta_color=dc)
d, dc = delta_show(cpc_conv, prv_cpc_cv, lower_is_better=True)
c3.metric("💬 Custo/Conversa", currency(cpc_conv) if conversations > 0 else "—", delta=d if conversations > 0 else None, delta_color=dc)
d, dc = delta_show(leads, prv_leads)
c4.metric("🎯 Leads", number(leads) if leads > 0 else "—", delta=d if leads > 0 else None, delta_color=dc)
d, dc = delta_show(cpl, prv_cpl, lower_is_better=True)
c5.metric("💸 CPL", currency(cpl) if leads > 0 else "—", delta=d if leads > 0 else None, delta_color=dc)

# Linha 2: eficiência
c6, c7, c8, _ = st.columns(4)
d, dc = delta_show(ctr, prv_ctr)
c6.metric("📊 CTR", percent(ctr), delta=d, delta_color=dc)
d, dc = delta_show(cpm, prv_cpm, lower_is_better=True)
c7.metric("💸 CPM", currency(cpm), delta=d, delta_color=dc)
d, dc = delta_show(cpc, prv_cpc, lower_is_better=True)
c8.metric("🖱️ CPC", currency(cpc), delta=d, delta_color=dc)

# ROAS — apenas se houver dados de e-commerce
revenue = df["purchase_value"].sum()
if revenue > 0:
    purchases = df["purchases"].sum()
    roas_val = revenue / spend if spend > 0 else 0
    cpa_val  = spend / purchases if purchases > 0 else 0
    prv_rev  = df_prev["purchase_value"].sum() if not df_prev.empty else 0
    prv_pur  = df_prev["purchases"].sum() if not df_prev.empty else 0
    prv_roas = prv_rev / prv_spend if prv_spend > 0 else 0
    prv_cpa  = prv_spend / prv_pur if prv_pur > 0 else 0
    with st.expander("📈 E-commerce / Vendas online (dados disponíveis)", expanded=False):
        rc1, rc2, rc3, rc4 = st.columns(4)
        d, dc = delta_show(revenue, prv_rev)
        rc1.metric("💵 Receita", currency(revenue), delta=d, delta_color=dc)
        d, dc = delta_show(roas_val, prv_roas)
        rc2.metric("🔁 ROAS", f"{roas_val:.2f}x", delta=d, delta_color=dc)
        d, dc = delta_show(purchases, prv_pur)
        rc3.metric("🛒 Compras", number(purchases), delta=d, delta_color=dc)
        d, dc = delta_show(cpa_val, prv_cpa, lower_is_better=True)
        rc4.metric("💸 CPA", currency(cpa_val), delta=d, delta_color=dc)

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = df.groupby("date").agg(
    spend=("spend", "sum"),
    conversations=("conversations", "sum"),
    leads=("leads", "sum"),
    clicks=("clicks", "sum"),
    impressions=("impressions", "sum"),
).reset_index()
daily["cpc_conv"] = daily.apply(lambda r: r["spend"] / r["conversations"] if r["conversations"] > 0 else 0, axis=1)
daily["cpl"]      = daily.apply(lambda r: r["spend"] / r["leads"] if r["leads"] > 0 else 0, axis=1)

daily_prev_conv  = df_prev.groupby("date").agg(conversations=("conversations", "sum")).reset_index() if not df_prev.empty else None
daily_prev_spend = df_prev.groupby("date").agg(spend=("spend", "sum")).reset_index() if not df_prev.empty else None

# Gráfico principal: conversas ou leads conforme o que houver
col_a, col_b = st.columns(2)
with col_a:
    if conversations > 0:
        st.plotly_chart(
            charts.line(daily, "date", "conversations", "Conversas iniciadas por dia", "Conversas",
                        color=charts.CYAN, prev_df=daily_prev_conv, prev_label="Conversas período anterior"),
            use_container_width=True,
        )
    else:
        st.plotly_chart(
            charts.line(daily, "date", "spend", "Investimento diário (R$)", "R$",
                        color=charts.BLUE, prev_df=daily_prev_spend, prev_label="Investimento período anterior"),
            use_container_width=True,
        )
with col_b:
    top_c = df.groupby("campaign_name").agg(
        conversations=("conversations", "sum"),
        leads=("leads", "sum"),
        spend=("spend", "sum"),
    ).reset_index()
    metric_col   = "conversations" if conversations > 0 else "leads"
    metric_label = "Conversas" if conversations > 0 else "Leads"
    top_c = top_c.sort_values(metric_col, ascending=False).head(8)[["campaign_name", metric_col]].copy()
    top_c.columns = ["Campanha", metric_label]
    st.plotly_chart(
        charts.bar(top_c, "Campanha", metric_label, f"Top campanhas por {metric_label}",
                   color=charts.CYAN if conversations > 0 else charts.GREEN, horizontal=True),
        use_container_width=True,
    )

col_c, col_d = st.columns(2)
with col_c:
    st.plotly_chart(
        charts.line(daily, "date", "spend", "Investimento diário (R$)", "R$",
                    color=charts.BLUE, prev_df=daily_prev_spend, prev_label="Investimento período anterior"),
        use_container_width=True,
    )
with col_d:
    if conversations > 0:
        st.plotly_chart(
            charts.line(daily, "date", "cpc_conv", "Custo por Conversa diário (R$)", "R$", color=charts.RED),
            use_container_width=True,
        )
    elif leads > 0:
        st.plotly_chart(
            charts.line(daily, "date", "cpl", "Custo por Lead diário (R$)", "R$", color=charts.RED),
            use_container_width=True,
        )
    else:
        daily["ctr"] = daily.apply(lambda r: r["clicks"] / r["impressions"] * 100 if r["impressions"] > 0 else 0, axis=1)
        st.plotly_chart(
            charts.line(daily, "date", "ctr", "CTR diário (%)", "%", color=charts.GREEN),
            use_container_width=True,
        )

st.divider()

# ── Tabela ─────────────────────────────────────────────────────────────────────
with st.expander("📋 Ver dados detalhados por campanha"):
    tbl = df.groupby("campaign_name").agg(
        Investimento=("spend", "sum"),
        Impressões=("impressions", "sum"),
        Cliques=("clicks", "sum"),
        Conversas=("conversations", "sum"),
        Leads=("leads", "sum"),
    ).reset_index().rename(columns={"campaign_name": "Campanha"})
    tbl["CTR (%)"]        = tbl.apply(lambda r: r["Cliques"] / r["Impressões"] * 100 if r["Impressões"] > 0 else 0, axis=1)
    tbl["CPL"]            = tbl.apply(lambda r: r["Investimento"] / r["Leads"] if r["Leads"] > 0 else 0, axis=1)
    tbl["Custo/Conversa"] = tbl.apply(lambda r: r["Investimento"] / r["Conversas"] if r["Conversas"] > 0 else 0, axis=1)
    tbl = tbl.drop(columns=["Impressões"]).sort_values("Investimento", ascending=False)
    st.dataframe(tbl.style.format({
        "Investimento":    lambda x: currency(x),
        "Cliques":         lambda x: number(x),
        "Conversas":       lambda x: number(x),
        "Leads":           lambda x: number(x),
        "CTR (%)":         lambda x: percent(x),
        "CPL":             lambda x: currency(x) if x > 0 else "—",
        "Custo/Conversa":  lambda x: currency(x) if x > 0 else "—",
    }), use_container_width=True)
