import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from utils.config_loader import load_config
from utils.meta_api import get_insights_with_comparison
from utils.formatters import currency, number, percent, delta_pct, top_insight
from utils.styles import css, section_header, insight_box
from utils import charts

st.set_page_config(
    page_title="Dashboard | Meta Ads",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(css(), unsafe_allow_html=True)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none!important;}</style>",
    unsafe_allow_html=True,
)

@st.cache_data(ttl=300)
def _load_config() -> dict:
    return load_config()


# ── Validação do token ─────────────────────────────────────────────────────────
token = st.query_params.get("token", "")

if not token:
    st.markdown(
        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'min-height:60vh;text-align:center;gap:1rem;">'
        '<div style="font-size:3rem;">📊</div>'
        '<h2 style="color:#F1ECF8;margin:0;">Meta Ads Dashboard</h2>'
        '<p style="color:#8B7EAF;margin:0;">Link de acesso não informado.<br>'
        'Solicite o link correto ao responsável pela conta.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

cfg     = _load_config()
account = next((c for c in cfg.get("contas", []) if c.get("client_token") == token and c.get("client_token")), None)

if not account:
    st.markdown(
        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'min-height:60vh;text-align:center;gap:1rem;">'
        '<div style="font-size:3rem;">🔒</div>'
        '<h2 style="color:#F1ECF8;margin:0;">Acesso inválido</h2>'
        '<p style="color:#EF4444;margin:0;">Token inválido ou acesso revogado.<br>'
        'Solicite um novo link ao responsável pela conta.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

account_id = account["account_id"]
label      = account.get("label", account_id)

st.session_state["_is_client"]    = True
st.session_state["_client_token"] = token

# Auto-refresh a cada 5 minutos
components.html(
    '<script>setTimeout(function(){window.top.location.reload();},300000);</script>',
    height=0,
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Meta Ads")

    # Badge da conta (locked)
    st.markdown(
        f'<div style="background:rgba(168,85,247,0.10);border:1px solid rgba(168,85,247,0.22);'
        f'border-radius:12px;padding:0.75rem 1rem;margin:0.5rem 0 1.2rem;">'
        f'<div style="color:#8B7EAF;font-size:0.70rem;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.10em;margin-bottom:0.3rem;">Conta</div>'
        f'<div style="color:#F1ECF8;font-size:1rem;font-weight:700;">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.caption("Período de análise")
    since = st.date_input("De",  value=datetime.today() - timedelta(days=29))
    until = st.date_input("Até", value=datetime.today() - timedelta(days=1))
    n_days = (until - since).days + 1
    st.caption(f"📅 {n_days} dias | comparando com {n_days} dias anteriores")

# ── Dados ──────────────────────────────────────────────────────────────────────
with st.spinner("Buscando dados..."):
    try:
        df_raw, df_prev_raw, prev_since, prev_until = get_insights_with_comparison(
            account_id, str(since), str(until)
        )
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        st.stop()

if df_raw.empty:
    st.warning("Nenhum dado encontrado para o período selecionado.")
    st.stop()

for _col in ("conversations", "cpc_conv"):
    if _col not in df_raw.columns:
        df_raw[_col] = 0
    if not df_prev_raw.empty and _col not in df_prev_raw.columns:
        df_prev_raw[_col] = 0

# ── Filtro de campanhas ────────────────────────────────────────────────────────
all_campaigns = sorted(df_raw["campaign_name"].unique().tolist())

with st.sidebar:
    st.divider()
    st.caption("Filtro de campanhas")

    _CK = "_cli_camp_ms"
    if _CK not in st.session_state:
        st.session_state[_CK] = []

    _ca, _cc = st.columns(2)
    if _ca.button("✓ Todas", key="cli_sel_all", use_container_width=True):
        st.session_state[_CK] = all_campaigns
        st.rerun()
    if _cc.button("✕ Limpar", key="cli_clr", use_container_width=True):
        st.session_state[_CK] = []
        st.rerun()

    sel_camps = st.multiselect(
        "campanhas",
        options=all_campaigns,
        key=_CK,
        placeholder=f"Todas ({len(all_campaigns)})",
        label_visibility="collapsed",
    )
    if sel_camps:
        st.caption(f"🎯 {len(sel_camps)} de {len(all_campaigns)} selecionadas")
    else:
        st.caption(f"📋 {len(all_campaigns)} campanhas")

if sel_camps:
    df      = df_raw[df_raw["campaign_name"].isin(sel_camps)].copy()
    df_prev = df_prev_raw[df_prev_raw["campaign_name"].isin(sel_camps)].copy() if not df_prev_raw.empty else df_prev_raw
else:
    df      = df_raw.copy()
    df_prev = df_prev_raw.copy()

if df.empty:
    st.warning("Nenhum dado para as campanhas selecionadas.")
    st.stop()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title(f"Relatório — {label}")
st.caption(
    f"{since.strftime('%d/%m/%Y')} → {until.strftime('%d/%m/%Y')}"
    f"  ·  {df['campaign_name'].nunique()} campanha(s)"
    f"  ·  {df['campaign_type'].nunique()} objetivo(s)"
    f"  ·  atualizado {datetime.now().strftime('%H:%M')}"
)

insight = top_insight(df, df_prev)
st.markdown(insight_box(insight), unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
def _ds(cur, prv, lower=False):
    d, pos = delta_pct(cur, prv)
    if lower and pos is not None:
        pos = not pos
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

prv_spend  = df_prev["spend"].sum()  if not df_prev.empty else 0
prv_leads  = df_prev["leads"].sum()  if not df_prev.empty else 0
prv_cpl    = prv_spend / prv_leads   if prv_leads  > 0 else 0
prv_conv   = df_prev["conversations"].sum() if not df_prev.empty else 0
prv_cpc_cv = prv_spend / prv_conv    if prv_conv   > 0 else 0
prv_imp    = df_prev["impressions"].sum() if not df_prev.empty else 0
prv_reach  = df_prev["reach"].sum()  if not df_prev.empty else 0
prv_clicks = df_prev["clicks"].sum() if not df_prev.empty else 0
prv_ctr    = prv_clicks / prv_imp * 100  if prv_imp    > 0 else 0
prv_cpm    = prv_spend  / prv_imp * 1000 if prv_imp    > 0 else 0
prv_cpc    = prv_spend  / prv_clicks     if prv_clicks > 0 else 0
prv_freq   = prv_imp    / prv_reach      if prv_reach  > 0 else 0

# Linha 1 — resultados
c1, c2, c3, c4, c5 = st.columns(5)
d, dc = _ds(total_spend, prv_spend)
c1.metric("💰 Investimento",    currency(total_spend), delta=d, delta_color=dc)
d, dc = _ds(total_leads, prv_leads)
c2.metric("🎯 Leads",           number(total_leads),   delta=d, delta_color=dc)
d, dc = _ds(cpl, prv_cpl, lower=True)
c3.metric("💸 CPL",             currency(cpl) if total_leads > 0 else "—",
          delta=d if total_leads > 0 else None, delta_color=dc)
d, dc = _ds(total_conv, prv_conv)
c4.metric("💬 Conversas",       number(total_conv) if total_conv > 0 else "—",
          delta=d if total_conv > 0 else None, delta_color=dc)
d, dc = _ds(cpc_conv, prv_cpc_cv, lower=True)
c5.metric("💬 Custo/Conversa",  currency(cpc_conv) if total_conv > 0 else "—",
          delta=d if total_conv > 0 else None, delta_color=dc)

# Linha 2 — eficiência
c6, c7, c8, c9 = st.columns(4)
d, dc = _ds(ctr, prv_ctr)
c6.metric("📊 CTR",         percent(ctr),      delta=d, delta_color=dc)
d, dc = _ds(cpm, prv_cpm, lower=True)
c7.metric("💸 CPM",         currency(cpm),     delta=d, delta_color=dc)
d, dc = _ds(cpc, prv_cpc, lower=True)
c8.metric("🖱️ CPC",         currency(cpc),     delta=d, delta_color=dc)
d, dc = _ds(freq, prv_freq, lower=True)
c9.metric("🔁 Frequência",  f"{freq:.2f}x",    delta=d, delta_color=dc)

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
daily = (
    df.groupby("date")
    .agg(spend=("spend","sum"), leads=("leads","sum"),
         impressions=("impressions","sum"), clicks=("clicks","sum"))
    .reset_index()
)

daily_prev_df = (
    df_prev.groupby("date").agg(spend=("spend","sum"), impressions=("impressions","sum")).reset_index()
    if not df_prev.empty else None
)

label_map = {
    "awareness": "Awareness", "traffic": "Tráfego",
    "leads": "Leads", "conversions": "Conversões", "other": "Outros",
}

st.markdown(section_header("Investimento", "evolução diária e distribuição por objetivo"), unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(
        charts.line(daily, "date", "spend", "Investimento diário (R$)", "R$", prev_df=daily_prev_df),
        use_container_width=True,
    )
with col_b:
    by_type = df.groupby("campaign_type")["spend"].sum().reset_index()
    by_type["campaign_type"] = by_type["campaign_type"].map(label_map).fillna("Outros")
    st.plotly_chart(
        charts.donut(by_type["campaign_type"].tolist(), by_type["spend"].tolist(),
                     "Distribuição por objetivo"),
        use_container_width=True,
    )

st.markdown(section_header("Leads & Eficiência", "geração de leads e frequência por campanha"), unsafe_allow_html=True)
col_c, col_d = st.columns(2)
with col_c:
    daily_leads_prev = (
        df_prev.groupby("date").agg(leads=("leads","sum")).reset_index()
        if not df_prev.empty else None
    )
    st.plotly_chart(
        charts.line(daily, "date", "leads", "Leads ao longo do tempo", "Leads",
                    color=charts.GREEN, prev_df=daily_leads_prev, prev_label="Leads período anterior"),
        use_container_width=True,
    )
with col_d:
    freq_camp = (
        df.groupby("campaign_name")
        .agg(impressions=("impressions","sum"), reach=("reach","sum"))
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

st.markdown(section_header("Cliques & Custo", "CTR por campanha e evolução do CPM"), unsafe_allow_html=True)
col_e, col_f = st.columns(2)
with col_e:
    ctr_camp = (
        df.groupby("campaign_name")
        .agg(clicks=("clicks","sum"), impressions=("impressions","sum"))
        .reset_index()
    )
    ctr_camp = ctr_camp[ctr_camp["impressions"] > 0].copy()
    ctr_camp["CTR (%)"] = ctr_camp["clicks"] / ctr_camp["impressions"] * 100
    ctr_camp = ctr_camp.sort_values("CTR (%)", ascending=False).head(8)
    ctr_camp = ctr_camp.rename(columns={"campaign_name": "Campanha"})
    st.plotly_chart(
        charts.bar(ctr_camp, "Campanha", "CTR (%)", "CTR por campanha (%)",
                   color=charts.CYAN, horizontal=True),
        use_container_width=True,
    )
with col_f:
    daily["cpm"] = daily.apply(
        lambda r: r["spend"] / r["impressions"] * 1000 if r["impressions"] > 0 else 0, axis=1
    )
    st.plotly_chart(
        charts.line(daily, "date", "cpm", "CPM ao longo do tempo (R$)", "R$",
                    color=charts.PURPLE),
        use_container_width=True,
    )

st.divider()

# ── Tabela detalhada ───────────────────────────────────────────────────────────
with st.expander("📋 Detalhamento por campanha"):
    summary = df.groupby(["campaign_name", "campaign_type"]).agg(
        Investimento=("spend",        "sum"),
        Impressões  =("impressions",  "sum"),
        Cliques     =("clicks",       "sum"),
        Leads       =("leads",        "sum"),
        Conversas   =("conversations","sum"),
    ).reset_index()

    summary["CTR (%)"]  = summary.apply(
        lambda r: r["Cliques"] / r["Impressões"] * 100 if r["Impressões"] > 0 else 0, axis=1)
    summary["CPM (R$)"] = summary.apply(
        lambda r: r["Investimento"] / r["Impressões"] * 1000 if r["Impressões"] > 0 else 0, axis=1)
    summary["CPL (R$)"] = summary.apply(
        lambda r: r["Investimento"] / r["Leads"] if r["Leads"] > 0 else 0, axis=1)
    summary["Frequência"] = summary.apply(
        lambda r: df[df["campaign_name"] == r["campaign_name"]]["impressions"].sum()
        / df[df["campaign_name"] == r["campaign_name"]]["reach"].sum()
        if df[df["campaign_name"] == r["campaign_name"]]["reach"].sum() > 0 else 0, axis=1)

    summary["campaign_type"] = summary["campaign_type"].map(label_map).fillna("Outros")
    summary = (
        summary
        .rename(columns={"campaign_name": "Campanha", "campaign_type": "Tipo"})
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
            "CPL (R$)":     lambda x: currency(x) if x > 0 else "—",
            "Frequência":   lambda x: f"{x:.2f}x",
        }),
        use_container_width=True,
        height=380,
        hide_index=True,
    )

st.caption(
    f"Meta Ads Dashboard  ·  Dados via Meta Ads API  ·  "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
