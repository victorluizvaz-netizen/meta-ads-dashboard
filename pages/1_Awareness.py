import streamlit as st
from utils.meta_api import get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils import charts
from utils.styles import css, insight_box

st.set_page_config(page_title="Awareness | Meta Ads", page_icon="📣", layout="wide")
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

df = df_all[df_all["campaign_type"] == "awareness"].copy()
df_prev = df_prev_all[df_prev_all["campaign_type"] == "awareness"].copy() if not df_prev_all.empty else df_prev_all

st.title("📣 Awareness")
st.caption(f"Alcance e visibilidade da marca  ·  {since} → {until}")

if df.empty:
    st.info("Nenhuma campanha de Awareness encontrada neste período.")
    st.stop()

st.markdown(insight_box(top_insight(df_all, df_prev_all, "awareness")), unsafe_allow_html=True)
st.page_link("pages/8_Campanhas.py", label="⚙️ Gerenciar campanhas deste período", icon="⚙️")

# ── KPIs ───────────────────────────────────────────────────────────────────────
def m(col, label, fmt, agg="sum", lower_is_better=False):
    cur = df[col].sum() if agg == "sum" else df[col].mean()
    prv = df_prev[col].sum() if (not df_prev.empty and col in df_prev.columns and agg=="sum") else (df_prev[col].mean() if (not df_prev.empty and col in df_prev.columns) else 0)
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    dc = "normal" if (pos is None or pos) else "inverse"
    return label, fmt(cur), d, dc

total_impressions = df["impressions"].sum()
total_reach = df["reach"].sum()
freq = total_impressions / total_reach if total_reach > 0 else 0
spend = df["spend"].sum()
cpm = spend / total_impressions * 1000 if total_impressions > 0 else 0

prv_imp = df_prev["impressions"].sum() if not df_prev.empty else 0
prv_reach = df_prev["reach"].sum() if not df_prev.empty else 0
prv_spend = df_prev["spend"].sum() if not df_prev.empty else 0
prv_cpm = prv_spend / prv_imp * 1000 if prv_imp > 0 else 0

def delta_show(cur, prv, lower_is_better=False):
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    return d, "normal" if (pos is None or pos) else "inverse"

c1, c2, c3, c4, c5 = st.columns(5)
d, dc = delta_show(total_reach, prv_reach)
c1.metric("📣 Alcance único", number(total_reach), delta=d, delta_color=dc)
d, dc = delta_show(total_impressions, prv_imp)
c2.metric("👁️ Impressões", number(total_impressions), delta=d, delta_color=dc)
c3.metric("🔁 Frequência", f"{freq:.2f}x")
d, dc = delta_show(cpm, prv_cpm, lower_is_better=True)
c4.metric("💸 CPM", currency(cpm), delta=d, delta_color=dc)
d, dc = delta_show(spend, prv_spend)
c5.metric("💰 Investimento", currency(spend), delta=d, delta_color=dc)

vp = df["video_plays"].sum()
tp = df["thruplays"].sum()
prv_vp = df_prev["video_plays"].sum() if not df_prev.empty else 0
prv_tp = df_prev["thruplays"].sum() if not df_prev.empty else 0
thruplay_rate = tp / vp * 100 if vp > 0 else 0

c6, c7, c8, _, _ = st.columns(5)
d, dc = delta_show(vp, prv_vp)
c6.metric("▶️ Reproduções de vídeo", number(vp), delta=d, delta_color=dc)
d, dc = delta_show(tp, prv_tp)
c7.metric("✅ ThruPlays", number(tp), delta=d, delta_color=dc)
c8.metric("📊 Taxa ThruPlay", percent(thruplay_rate))

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = df.groupby("date").agg(reach=("reach","sum"), impressions=("impressions","sum"), spend=("spend","sum")).reset_index()
daily_prev = df_prev.groupby("date").agg(reach=("reach","sum")).reset_index() if not df_prev.empty else None

col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.line(daily, "date", "reach", "Alcance diário — pessoas únicas impactadas", "Pessoas", prev_df=daily_prev, prev_label="Alcance período anterior"),
        use_container_width=True,
    )
with col_b:
    st.plotly_chart(
        charts.multiline(daily, "date", [("impressions","Impressões"),("reach","Alcance")], "Impressões vs Alcance"),
        use_container_width=True,
    )

col_c, col_d = st.columns(2)
with col_c:
    st.plotly_chart(
        charts.line(daily, "date", "spend", "Investimento diário (R$)", "R$", color=charts.ORANGE),
        use_container_width=True,
    )
with col_d:
    top_c = df.groupby("campaign_name")["reach"].sum().sort_values(ascending=False).head(8).reset_index()
    top_c.columns = ["Campanha", "Alcance"]
    st.plotly_chart(
        charts.bar(top_c, "Campanha", "Alcance", "Campanhas com maior alcance", horizontal=True),
        use_container_width=True,
    )

st.divider()

with st.expander("📋 Ver dados detalhados por campanha"):
    tbl = df.groupby("campaign_name").agg(
        Investimento=("spend","sum"), Impressões=("impressions","sum"),
        Alcance=("reach","sum"), Reproduções=("video_plays","sum"), ThruPlays=("thruplays","sum"),
    ).reset_index().rename(columns={"campaign_name":"Campanha"})
    tbl["Frequência"] = tbl["Impressões"] / tbl["Alcance"]
    tbl["CPM"] = tbl.apply(lambda r: r["Investimento"]/r["Impressões"]*1000 if r["Impressões"]>0 else 0, axis=1)
    tbl = tbl.sort_values("Alcance", ascending=False)
    st.dataframe(tbl.style.format({
        "Investimento": lambda x: currency(x), "Impressões": lambda x: number(x),
        "Alcance": lambda x: number(x), "Frequência": lambda x: f"{x:.2f}x",
        "CPM": lambda x: currency(x), "Reproduções": lambda x: number(x), "ThruPlays": lambda x: number(x),
    }), use_container_width=True)
