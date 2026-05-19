import streamlit as st
from utils.meta_api import get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils import charts
from utils.styles import css, insight_box

st.set_page_config(page_title="Leads | Meta Ads", page_icon="🎯", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

from utils.client_guard import redirect_if_client
redirect_if_client()

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

selected = st.session_state.get("selected_campaigns", [])
if selected:
    df_all = df_all[df_all["campaign_name"].isin(selected)]
    if not df_prev_all.empty:
        df_prev_all = df_prev_all[df_prev_all["campaign_name"].isin(selected)]

df = df_all[df_all["campaign_type"] == "leads"].copy()
df_prev = df_prev_all[df_prev_all["campaign_type"] == "leads"].copy() if not df_prev_all.empty else df_prev_all

st.title("🎯 Geração de Leads")
st.caption(f"Volume, custo e qualidade dos leads  ·  {since} → {until}")

if df.empty:
    st.info("Nenhuma campanha de Leads encontrada neste período.")
    st.stop()

st.markdown(insight_box(top_insight(df_all, df_prev_all, "leads")), unsafe_allow_html=True)
st.page_link("pages/8_Campanhas.py", label="⚙️ Gerenciar campanhas deste período", icon="⚙️")

# ── KPIs ───────────────────────────────────────────────────────────────────────
def delta_show(cur, prv, lower_is_better=False):
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    return d, "normal" if (pos is None or pos) else "inverse"

total_leads = df["leads"].sum()
spend = df["spend"].sum()
cpl = spend / total_leads if total_leads > 0 else 0
impressions = df["impressions"].sum()
clicks = df["clicks"].sum()
ctr = clicks / impressions * 100 if impressions > 0 else 0
lead_rate = total_leads / clicks * 100 if clicks > 0 else 0

prv_leads = df_prev["leads"].sum() if not df_prev.empty else 0
prv_spend = df_prev["spend"].sum() if not df_prev.empty else 0
prv_cpl = prv_spend / prv_leads if prv_leads > 0 else 0
prv_clicks = df_prev["clicks"].sum() if not df_prev.empty else 0
prv_lr = prv_leads / prv_clicks * 100 if prv_clicks > 0 else 0

c1, c2, c3, c4 = st.columns(4)
d, dc = delta_show(total_leads, prv_leads)
c1.metric("🎯 Leads gerados", number(total_leads), delta=d, delta_color=dc)
d, dc = delta_show(cpl, prv_cpl, lower_is_better=True)
c2.metric("💸 Custo por Lead (CPL)", currency(cpl), delta=d, delta_color=dc)
d, dc = delta_show(spend, prv_spend)
c3.metric("💰 Investimento", currency(spend), delta=d, delta_color=dc)
d, dc = delta_show(lead_rate, prv_lr)
c4.metric("📉 Taxa de lead", percent(lead_rate), delta=d, delta_color=dc)

c5, c6, c7, _ = st.columns(4)
c5.metric("👁️ Impressões", number(impressions))
c6.metric("🖱️ Cliques", number(clicks))
c7.metric("📊 CTR", percent(ctr))

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = df.groupby("date").agg(leads=("leads","sum"), spend=("spend","sum")).reset_index()
daily["cpl"] = daily.apply(lambda r: r["spend"]/r["leads"] if r["leads"]>0 else 0, axis=1)
daily_prev = df_prev.groupby("date").agg(leads=("leads","sum")).reset_index() if not df_prev.empty else None

col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.line(daily, "date", "leads", "Leads gerados por dia", "Leads", color=charts.GREEN, prev_df=daily_prev, prev_label="Leads período anterior"),
        use_container_width=True,
    )
with col_b:
    st.plotly_chart(
        charts.line(daily, "date", "cpl", "Custo por Lead diário (R$)", "R$", color=charts.RED),
        use_container_width=True,
    )

col_c, col_d = st.columns(2)
with col_c:
    st.plotly_chart(
        charts.multiline(daily, "date", [("spend","Investimento (R$)"),("leads","Leads")], "Investimento vs Leads"),
        use_container_width=True,
    )
with col_d:
    top_c = df.groupby("campaign_name").agg(leads=("leads","sum"), spend=("spend","sum")).reset_index()
    top_c["cpl"] = top_c.apply(lambda r: r["spend"]/r["leads"] if r["leads"]>0 else 0, axis=1)
    top_c = top_c.sort_values("leads", ascending=False).head(8)
    top_c.columns = ["Campanha","Leads","Investimento","CPL"]
    st.plotly_chart(
        charts.bar(top_c, "Campanha", "Leads", "Campanhas com mais leads", color=charts.GREEN, horizontal=True),
        use_container_width=True,
    )

st.divider()

with st.expander("📋 Ver dados detalhados por campanha"):
    tbl = df.groupby("campaign_name").agg(
        Investimento=("spend","sum"), Cliques=("clicks","sum"), Leads=("leads","sum"),
    ).reset_index().rename(columns={"campaign_name":"Campanha"})
    tbl["CPL"] = tbl.apply(lambda r: r["Investimento"]/r["Leads"] if r["Leads"]>0 else 0, axis=1)
    tbl["Taxa de Lead"] = tbl.apply(lambda r: r["Leads"]/r["Cliques"]*100 if r["Cliques"]>0 else 0, axis=1)
    tbl = tbl.sort_values("Leads", ascending=False)
    st.dataframe(tbl.style.format({
        "Investimento": lambda x: currency(x), "Cliques": lambda x: number(x),
        "Leads": lambda x: number(x), "CPL": lambda x: currency(x), "Taxa de Lead": lambda x: percent(x),
    }), use_container_width=True)
