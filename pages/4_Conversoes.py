import streamlit as st
from utils.meta_api import get_insights_with_comparison
from utils.formatters import currency, number, percent, roas, delta_pct, top_insight
from utils import charts
from utils.styles import css, insight_box, warning_box, roas_box

st.set_page_config(page_title="Conversões | Meta Ads", page_icon="🛒", layout="wide")
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

st.title("🛒 Conversões e Vendas")
st.caption(f"ROAS, receita e custo por aquisição  ·  {since} → {until}")

if df.empty:
    st.info("Nenhuma campanha de Conversões encontrada neste período.")
    st.stop()

st.markdown(insight_box(top_insight(df_all, df_prev_all, "conversions")), unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
def delta_show(cur, prv, lower_is_better=False):
    d, pos = delta_pct(cur, prv)
    if lower_is_better and pos is not None: pos = not pos
    return d, "normal" if (pos is None or pos) else "inverse"

spend = df["spend"].sum()
revenue = df["purchase_value"].sum()
purchases = df["purchases"].sum()
roas_val = revenue / spend if spend > 0 else 0
cpa_val = spend / purchases if purchases > 0 else 0
clicks = df["clicks"].sum()
impressions = df["impressions"].sum()
conv_rate = purchases / clicks * 100 if clicks > 0 else 0
conversations = df["conversations"].sum()
cpc_conv = spend / conversations if conversations > 0 else 0

prv_spend = df_prev["spend"].sum() if not df_prev.empty else 0
prv_rev = df_prev["purchase_value"].sum() if not df_prev.empty else 0
prv_pur = df_prev["purchases"].sum() if not df_prev.empty else 0
prv_roas = prv_rev / prv_spend if prv_spend > 0 else 0
prv_cpa = prv_spend / prv_pur if prv_pur > 0 else 0
prv_conv = df_prev["conversations"].sum() if not df_prev.empty else 0
prv_cpc_conv = prv_spend / prv_conv if prv_conv > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
d, dc = delta_show(revenue, prv_rev)
c1.metric("💵 Receita gerada", currency(revenue), delta=d, delta_color=dc)
d, dc = delta_show(roas_val, prv_roas)
c2.metric("🔁 ROAS", roas(roas_val), delta=d, delta_color=dc)
d, dc = delta_show(purchases, prv_pur)
c3.metric("🛒 Compras", number(purchases), delta=d, delta_color=dc)
d, dc = delta_show(cpa_val, prv_cpa, lower_is_better=True)
c4.metric("💸 Custo por Compra (CPA)", currency(cpa_val), delta=d, delta_color=dc)
d, dc = delta_show(spend, prv_spend)
c5.metric("💰 Investimento", currency(spend), delta=d, delta_color=dc)

if conversations > 0:
    c6, c7, _, _, _ = st.columns(5)
    d, dc = delta_show(conversations, prv_conv)
    c6.metric("💬 Conversas iniciadas", number(conversations), delta=d, delta_color=dc)
    d, dc = delta_show(cpc_conv, prv_cpc_conv, lower_is_better=True)
    c7.metric("💬 Custo por Conversa", currency(cpc_conv), delta=d, delta_color=dc)

st.markdown(roas_box(roas_val), unsafe_allow_html=True)

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = df.groupby("date").agg(spend=("spend","sum"), purchase_value=("purchase_value","sum"), purchases=("purchases","sum")).reset_index()
daily["roas"] = daily.apply(lambda r: r["purchase_value"]/r["spend"] if r["spend"]>0 else 0, axis=1)
daily["cpa"] = daily.apply(lambda r: r["spend"]/r["purchases"] if r["purchases"]>0 else 0, axis=1)
daily_prev = df_prev.groupby("date").agg(purchase_value=("purchase_value","sum")).reset_index() if not df_prev.empty else None

col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.multiline(daily, "date", [("purchase_value","Receita (R$)"),("spend","Investimento (R$)")], "Receita vs Investimento diário"),
        use_container_width=True,
    )
with col_b:
    st.plotly_chart(
        charts.line(daily, "date", "roas", "ROAS diário — quanto retorna por R$ investido", "ROAS", color=charts.GREEN, prev_df=daily_prev if daily_prev is not None else None, prev_label="ROAS período anterior"),
        use_container_width=True,
    )

col_c, col_d = st.columns(2)
with col_c:
    st.plotly_chart(
        charts.line(daily, "date", "purchases", "Compras por dia", "Compras", color=charts.PURPLE),
        use_container_width=True,
    )
with col_d:
    st.plotly_chart(
        charts.line(daily, "date", "cpa", "Custo por Compra diário (R$)", "R$", color=charts.RED),
        use_container_width=True,
    )

st.divider()

with st.expander("📋 Ver dados detalhados por campanha"):
    tbl = df.groupby("campaign_name").agg(
        Investimento=("spend","sum"), Cliques=("clicks","sum"),
        Conversas=("conversations","sum"), Compras=("purchases","sum"), Receita=("purchase_value","sum"),
    ).reset_index().rename(columns={"campaign_name":"Campanha"})
    tbl["ROAS"] = tbl.apply(lambda r: r["Receita"]/r["Investimento"] if r["Investimento"]>0 else 0, axis=1)
    tbl["CPA"] = tbl.apply(lambda r: r["Investimento"]/r["Compras"] if r["Compras"]>0 else 0, axis=1)
    tbl["Custo/Conversa"] = tbl.apply(lambda r: r["Investimento"]/r["Conversas"] if r["Conversas"]>0 else 0, axis=1)
    tbl = tbl.sort_values("Receita", ascending=False)
    st.dataframe(tbl.style.format({
        "Investimento": lambda x: currency(x), "Cliques": lambda x: number(x),
        "Conversas": lambda x: number(x), "Compras": lambda x: number(x),
        "Receita": lambda x: currency(x), "ROAS": lambda x: f"{x:.2f}x",
        "CPA": lambda x: currency(x), "Custo/Conversa": lambda x: currency(x) if x > 0 else "—",
    }), use_container_width=True)
