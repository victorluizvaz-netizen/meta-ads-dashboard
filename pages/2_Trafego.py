import streamlit as st
from utils.meta_api import get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils import charts
from utils.styles import css, insight_box

st.set_page_config(page_title="Tráfego | Meta Ads", page_icon="🚦", layout="wide")
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

selected = st.session_state.get("selected_campaigns", [])
if selected:
    df_all = df_all[df_all["campaign_name"].isin(selected)]
    if not df_prev_all.empty:
        df_prev_all = df_prev_all[df_prev_all["campaign_name"].isin(selected)]

df = df_all[df_all["campaign_type"] == "traffic"].copy()
df_prev = df_prev_all[df_prev_all["campaign_type"] == "traffic"].copy() if not df_prev_all.empty else df_prev_all

st.title("🚦 Tráfego")
st.caption(f"Cliques, visitas e comportamento do público  ·  {since} → {until}")

if df.empty:
    st.info("Nenhuma campanha de Tráfego encontrada neste período.")
    st.stop()

st.markdown(insight_box(top_insight(df_all, df_prev_all, "traffic")), unsafe_allow_html=True)
st.page_link("pages/8_Campanhas.py", label="⚙️ Gerenciar campanhas deste período", icon="⚙️")

# ── KPIs ───────────────────────────────────────────────────────────────────────
def delta_show(cur, prv, lower_is_better=False):
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    return d, "normal" if (pos is None or pos) else "inverse"

clicks = df["clicks"].sum()
link_clicks = df["link_clicks"].sum()
lp_views = df["landing_page_views"].sum()
spend = df["spend"].sum()
impressions = df["impressions"].sum()
ctr = clicks / impressions * 100 if impressions > 0 else 0
cpc = spend / clicks if clicks > 0 else 0
lp_rate = lp_views / link_clicks * 100 if link_clicks > 0 else 0

prv = lambda col: df_prev[col].sum() if (not df_prev.empty and col in df_prev.columns) else 0
prv_clicks = prv("clicks"); prv_lc = prv("link_clicks"); prv_lp = prv("landing_page_views")
prv_spend = prv("spend"); prv_imp = prv("impressions")
prv_ctr = prv_clicks / prv_imp * 100 if prv_imp > 0 else 0
prv_cpc = prv_spend / prv_clicks if prv_clicks > 0 else 0

c1, c2, c3, c4 = st.columns(4)
d, dc = delta_show(clicks, prv_clicks)
c1.metric("🖱️ Cliques totais", number(clicks), delta=d, delta_color=dc)
d, dc = delta_show(link_clicks, prv_lc)
c2.metric("🔗 Cliques no link", number(link_clicks), delta=d, delta_color=dc)
d, dc = delta_show(lp_views, prv_lp)
c3.metric("🌐 Visualizações de página", number(lp_views), delta=d, delta_color=dc)
d, dc = delta_show(spend, prv_spend)
c4.metric("💰 Investimento", currency(spend), delta=d, delta_color=dc)

c5, c6, c7, c8 = st.columns(4)
d, dc = delta_show(ctr, prv_ctr)
c5.metric("📊 Taxa de Cliques (CTR)", percent(ctr), delta=d, delta_color=dc)
d, dc = delta_show(cpc, prv_cpc, lower_is_better=True)
c6.metric("💸 Custo por Clique (CPC)", currency(cpc), delta=d, delta_color=dc)
c7.metric("💸 CPM", currency(df["cpm"].mean()))
c8.metric("📉 Taxa LP", percent(lp_rate))

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = df.groupby("date").agg(clicks=("clicks","sum"), link_clicks=("link_clicks","sum"), lp=("landing_page_views","sum"), cpc=("cpc","mean")).reset_index()
daily_prev = df_prev.groupby("date").agg(clicks=("clicks","sum")).reset_index() if not df_prev.empty else None

col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.line(daily, "date", "link_clicks", "Cliques no link por dia", "Cliques", color=charts.BLUE, prev_df=daily_prev, prev_label="Cliques período anterior"),
        use_container_width=True,
    )
with col_b:
    st.plotly_chart(
        charts.multiline(daily, "date", [("clicks","Cliques totais"),("link_clicks","Cliques no link"),("lp","Views de página")], "Funil de cliques diário"),
        use_container_width=True,
    )

col_c, col_d = st.columns(2)
with col_c:
    st.plotly_chart(
        charts.line(daily, "date", "cpc", "Custo por Clique diário (R$)", "R$", color=charts.ORANGE),
        use_container_width=True,
    )
with col_d:
    top_c = df.groupby("campaign_name")["link_clicks"].sum().sort_values(ascending=False).head(8).reset_index()
    top_c.columns = ["Campanha", "Cliques no Link"]
    st.plotly_chart(
        charts.bar(top_c, "Campanha", "Cliques no Link", "Campanhas com mais cliques no link", horizontal=True),
        use_container_width=True,
    )

st.divider()

with st.expander("📋 Ver dados detalhados por campanha"):
    tbl = df.groupby("campaign_name").agg(
        Investimento=("spend","sum"), Cliques=("clicks","sum"),
        Link_Clicks=("link_clicks","sum"), LP_Views=("landing_page_views","sum"),
    ).reset_index().rename(columns={"campaign_name":"Campanha","Link_Clicks":"Cliques no Link","LP_Views":"Views de Página"})
    tbl["CTR"] = tbl["Cliques"] / df.groupby("campaign_name")["impressions"].sum().values * 100
    tbl["CPC"] = tbl.apply(lambda r: r["Investimento"]/r["Cliques"] if r["Cliques"]>0 else 0, axis=1)
    tbl = tbl.sort_values("Cliques no Link", ascending=False)
    st.dataframe(tbl.style.format({
        "Investimento": lambda x: currency(x), "Cliques": lambda x: number(x),
        "Cliques no Link": lambda x: number(x), "Views de Página": lambda x: number(x),
        "CTR": lambda x: percent(x), "CPC": lambda x: currency(x),
    }), use_container_width=True)
