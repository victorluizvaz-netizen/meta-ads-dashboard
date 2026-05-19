import streamlit as st
from utils.meta_api import get_ad_insights, get_ads_management, update_status
from utils.formatters import currency, number, percent
from utils.styles import css, section_header
from utils import charts

st.set_page_config(page_title="Criativos | Meta Ads", page_icon="🎨", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

from utils.client_guard import redirect_if_client
redirect_if_client()

account_id = st.session_state.get("account_id")
since      = st.session_state.get("since")
until      = st.session_state.get("until")
selected   = st.session_state.get("selected_campaigns", [])

if not account_id:
    st.warning("⚠️ Volte à página principal e selecione uma conta.")
    st.stop()

st.title("🎨 Criativos — Análise por Anúncio")
st.caption(f"{since} → {until}")

with st.spinner("Buscando dados de anúncios..."):
    try:
        df_raw = get_ad_insights(account_id, since, until)
    except Exception as e:
        st.error(f"Erro ao buscar anúncios: {e}")
        st.stop()

if df_raw.empty:
    st.warning("Nenhum dado de anúncios encontrado para o período.")
    st.stop()

for _col in ("conversations",):
    if _col not in df_raw.columns:
        df_raw[_col] = 0

if selected:
    df = df_raw[df_raw["campaign_name"].isin(selected)].copy()
else:
    df = df_raw.copy()

if df.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

# ── Filtros locais (conjunto e anúncio) ──────────────────────────────────────
all_adsets_c = sorted(df["adset_name"].unique().tolist()) if "adset_name" in df.columns else []
all_ads_c    = sorted(df["ad_name"].unique().tolist())

_ADC_KEY = "_criativo_adset_ms"
_ADA_KEY = "_criativo_ad_ms"
if _ADC_KEY not in st.session_state:
    st.session_state[_ADC_KEY] = []
if _ADA_KEY not in st.session_state:
    st.session_state[_ADA_KEY] = []

col_f1, col_f2, col_clr = st.columns([2, 2, 1])
with col_f1:
    sel_adsets_c = st.multiselect(
        "Conjunto",
        options=all_adsets_c,
        key=_ADC_KEY,
        placeholder=f"Buscar conjunto... ({len(all_adsets_c)} disponíveis)",
    )
with col_f2:
    sel_ads_c = st.multiselect(
        "Anúncio",
        options=all_ads_c,
        key=_ADA_KEY,
        placeholder=f"Buscar anúncio... ({len(all_ads_c)} disponíveis)",
    )
if col_clr.button("✕ Limpar", key="criativo_clr_all", use_container_width=True):
    st.session_state[_ADC_KEY] = []
    st.session_state[_ADA_KEY] = []
    st.rerun()

if sel_adsets_c:
    df = df[df["adset_name"].isin(sel_adsets_c)].copy()
if sel_ads_c:
    df = df[df["ad_name"].isin(sel_ads_c)].copy()

if df.empty:
    st.warning("Nenhum anúncio encontrado com os filtros aplicados.")
    st.stop()

_filter_parts = []
if sel_adsets_c: _filter_parts.append(f"{len(sel_adsets_c)} conjunto(s)")
if sel_ads_c:    _filter_parts.append(f"{len(sel_ads_c)} anúncio(s)")
if _filter_parts:
    st.caption(f"🔍 Filtrando por: {', '.join(_filter_parts)}")

st.divider()

# Colunas derivadas
df["roas_v"] = df.apply(lambda r: r["purchase_value"] / r["spend"] if r["spend"] > 0 else 0, axis=1)
df["cpl_v"]  = df.apply(lambda r: r["spend"] / r["leads"]          if r["leads"]  > 0 else 0, axis=1)
df["cpa_v"]  = df.apply(lambda r: r["spend"] / r["purchases"]      if r["purchases"] > 0 else 0, axis=1)

# ── KPIs ─────────────────────────────────────────────────────────────────────
n_ads        = df["ad_id"].nunique() if "ad_id" in df.columns else len(df)
total_spend  = df["spend"].sum()
avg_ctr      = df["clicks"].sum() / df["impressions"].sum() * 100 if df["impressions"].sum() > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("🎨 Anúncios ativos",   number(n_ads))
c2.metric("💰 Investimento total", currency(total_spend))
c3.metric("👁️ Impressões totais", number(df["impressions"].sum()))
c4.metric("📊 CTR médio",          percent(avg_ctr))

st.divider()

# ── Tabs: melhor CTR / maior invest / leads / conversões ─────────────────────
tabs = st.tabs(["🏆 Melhor CTR", "💰 Maior Investimento", "🎯 Mais Leads", "🛒 Mais Conversões"])

def _two_col(df_tab, bar_x, bar_y, bar_title, bar_color, table_cols, table_rename, table_fmt):
    if df_tab.empty:
        st.info("Nenhum anúncio com dados suficientes no período.")
        return
    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        st.plotly_chart(
            charts.bar(df_tab.rename(columns={bar_x: bar_x, bar_y: bar_y}),
                       bar_x, bar_y, bar_title, horizontal=True, color=bar_color),
            use_container_width=True,
        )
    with col_b:
        show = df_tab[[c for c in table_cols if c in df_tab.columns]].rename(columns=table_rename)
        st.dataframe(
            show.style.format({k: v for k, v in table_fmt.items() if k in show.columns}),
            use_container_width=True,
        )

with tabs[0]:  # Melhor CTR
    top_ctr = df[df["ctr"] > 0].sort_values("ctr", ascending=False).head(10)
    _two_col(
        top_ctr, "ad_name", "ctr", "Top 10 anúncios por CTR (%)", charts.GREEN,
        ["ad_name", "adset_name", "impressions", "clicks", "ctr", "spend"],
        {"ad_name": "Anúncio", "adset_name": "Conjunto", "impressions": "Impressões",
         "clicks": "Cliques", "ctr": "CTR %", "spend": "Invest."},
        {"CTR %": percent, "Invest.": currency, "Impressões": number, "Cliques": number},
    )

with tabs[1]:  # Maior investimento
    top_spend = df.sort_values("spend", ascending=False).head(10)
    _two_col(
        top_spend, "ad_name", "spend", "Top 10 anúncios por investimento", charts.BLUE,
        ["ad_name", "adset_name", "spend", "impressions", "clicks", "ctr"],
        {"ad_name": "Anúncio", "adset_name": "Conjunto", "spend": "Invest.",
         "impressions": "Impressões", "clicks": "Cliques", "ctr": "CTR %"},
        {"Invest.": currency, "CTR %": percent, "Impressões": number, "Cliques": number},
    )

with tabs[2]:  # Mais leads
    top_leads = df[df["leads"] > 0].sort_values("leads", ascending=False).head(10)
    _two_col(
        top_leads, "ad_name", "leads", "Top 10 anúncios por leads", charts.GREEN,
        ["ad_name", "adset_name", "leads", "cpl_v", "spend", "ctr"],
        {"ad_name": "Anúncio", "adset_name": "Conjunto", "leads": "Leads",
         "cpl_v": "CPL", "spend": "Invest.", "ctr": "CTR %"},
        {"CPL": currency, "Invest.": currency, "CTR %": percent, "Leads": number},
    )

with tabs[3]:  # Mais conversões
    top_conv = df[df["purchases"] > 0].sort_values("purchase_value", ascending=False).head(10)
    _two_col(
        top_conv, "ad_name", "roas_v", "Top 10 anúncios por ROAS", charts.GREEN,
        ["ad_name", "adset_name", "purchase_value", "roas_v", "purchases", "cpa_v", "spend"],
        {"ad_name": "Anúncio", "adset_name": "Conjunto", "purchase_value": "Receita",
         "roas_v": "ROAS", "purchases": "Compras", "cpa_v": "CPA", "spend": "Invest."},
        {"Receita": currency, "ROAS": lambda v: f"{v:.2f}x", "CPA": currency,
         "Invest.": currency, "Compras": number},
    )

st.divider()

# ── Comparativo: destaque vs baixo desempenho ─────────────────────────────────
st.markdown(section_header("Destaque vs Baixo Desempenho", "Anúncios com maior e menor CTR (mín. 500 impressões)"), unsafe_allow_html=True)

df_vol = df[df["impressions"] >= 500].copy()
if not df_vol.empty and df_vol["ctr"].sum() > 0:
    col_good, col_bad = st.columns(2)
    with col_good:
        st.markdown('<p style="color:#6EE7B7;font-size:0.85rem;font-weight:600;margin-bottom:0.4rem;">🟢 Melhor CTR</p>', unsafe_allow_html=True)
        best = df_vol.sort_values("ctr", ascending=False).head(5)[["ad_name", "adset_name", "ctr", "impressions", "spend"]]
        st.dataframe(best.rename(columns={"ad_name": "Anúncio", "adset_name": "Conjunto",
                                           "ctr": "CTR %", "impressions": "Impressões", "spend": "Invest."})
                       .style.format({"CTR %": percent, "Invest.": currency, "Impressões": number}),
                     use_container_width=True)
    with col_bad:
        st.markdown('<p style="color:#FCA5A5;font-size:0.85rem;font-weight:600;margin-bottom:0.4rem;">🔴 Menor CTR</p>', unsafe_allow_html=True)
        worst = df_vol.sort_values("ctr").head(5)[["ad_name", "adset_name", "ctr", "impressions", "spend"]]
        st.dataframe(worst.rename(columns={"ad_name": "Anúncio", "adset_name": "Conjunto",
                                            "ctr": "CTR %", "impressions": "Impressões", "spend": "Invest."})
                       .style.format({"CTR %": percent, "Invest.": currency, "Impressões": number}),
                     use_container_width=True)
else:
    st.info("Volume insuficiente para comparativo (mínimo 500 impressões por anúncio).")

st.divider()

# ── Controles de anúncio ──────────────────────────────────────────────────────
STATUS_ICON = {"ACTIVE": "🟢", "PAUSED": "🟡", "WITH_ISSUES": "🔴"}

with st.expander("⚙️ Controles de Anúncio", expanded=False):
    col_hdr, col_btn = st.columns([6, 1])
    col_hdr.markdown("**Pausar ou ativar anúncios individualmente**")
    if col_btn.button("🔄 Atualizar", key="refresh_ads", use_container_width=True):
        get_ads_management.clear()
        st.rerun()

    with st.spinner("Carregando anúncios..."):
        try:
            ads_mgmt = get_ads_management(account_id)
        except Exception as e:
            st.error(f"Erro ao carregar anúncios: {e}")
            st.stop()

    if selected:
        ad_ids_in_view = set(df["ad_id"].astype(str).tolist()) if "ad_id" in df.columns else set()
        ads_mgmt = [a for a in ads_mgmt if a["id"] in ad_ids_in_view]

    if not ads_mgmt:
        st.info("Nenhum anúncio encontrado.")
    else:
        ad_labels = [f"{STATUS_ICON.get(a['status'], '⚪')} {a['name']}" for a in ads_mgmt]
        sel_ad_idx = st.selectbox(
            "Selecione o anúncio",
            range(len(ad_labels)),
            format_func=lambda i: ad_labels[i],
            key="ad_sel",
        )

        if st.session_state.get("_last_ad_sel") != sel_ad_idx:
            st.session_state.pop("_ad_confirm_status", None)
            st.session_state["_last_ad_sel"] = sel_ad_idx

        ad = ads_mgmt[sel_ad_idx]

        col_info, col_act = st.columns([3, 2])
        with col_info:
            st.markdown(f"**Anúncio:** {ad['name']}")
            st.markdown(f"**Status:** {STATUS_ICON.get(ad['status'], '⚪')} `{ad['status']}`")

        with col_act:
            if ad["status"] == "ACTIVE":
                if st.button("⏸️ Pausar anúncio", type="primary", use_container_width=True, key="ad_pause"):
                    st.session_state["_ad_confirm_status"] = {"id": ad["id"], "name": ad["name"], "new_status": "PAUSED"}
            else:
                if st.button("▶️ Ativar anúncio", type="primary", use_container_width=True, key="ad_activate"):
                    st.session_state["_ad_confirm_status"] = {"id": ad["id"], "name": ad["name"], "new_status": "ACTIVE"}

        if "_ad_confirm_status" in st.session_state:
            cs = st.session_state["_ad_confirm_status"]
            action = "pausar" if cs["new_status"] == "PAUSED" else "ativar"
            st.warning(f"Confirma **{action}** o anúncio **{cs['name']}**?")
            c1, c2, _ = st.columns([1, 1, 3])
            if c1.button("✅ Confirmar", key="ad_yes_status"):
                try:
                    update_status(cs["id"], cs["new_status"])
                    st.success(f"Anúncio {'pausado' if cs['new_status'] == 'PAUSED' else 'ativado'} com sucesso!")
                    st.session_state.pop("_ad_confirm_status", None)
                    get_ads_management.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
            if c2.button("❌ Cancelar", key="ad_no_status"):
                st.session_state.pop("_ad_confirm_status", None)
                st.rerun()

st.divider()

# ── Tabela completa ───────────────────────────────────────────────────────────
with st.expander("📋 Todos os anúncios"):
    all_display = df[[
        "ad_name", "adset_name", "campaign_name", "spend", "impressions",
        "clicks", "ctr", "cpc", "leads", "cpl_v", "purchases", "roas_v",
    ]].rename(columns={
        "ad_name": "Anúncio", "adset_name": "Conjunto", "campaign_name": "Campanha",
        "spend": "Invest.", "impressions": "Impressões", "clicks": "Cliques",
        "ctr": "CTR %", "cpc": "CPC", "leads": "Leads",
        "cpl_v": "CPL", "purchases": "Compras", "roas_v": "ROAS",
    }).sort_values("Invest.", ascending=False)

    st.dataframe(
        all_display.style.format({
            "Invest.": currency, "CTR %": percent, "CPC": currency,
            "CPL": currency, "ROAS": lambda v: f"{v:.2f}x",
            "Impressões": number, "Cliques": number, "Leads": number, "Compras": number,
        }),
        use_container_width=True,
        height=520,
    )
