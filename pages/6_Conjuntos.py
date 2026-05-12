import streamlit as st
from utils.meta_api import (
    get_adset_insights_with_comparison, get_insights_with_comparison,
    get_adsets_management, get_campaigns_management, update_status, update_budget,
)
from utils.formatters import currency, number, percent, delta_pct
from utils.styles import css, section_header
from utils.alerts import generate_alerts
from utils import charts

st.set_page_config(page_title="Conjuntos de Anúncios | Meta Ads", page_icon="🗂️", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

account_id = st.session_state.get("account_id")
since      = st.session_state.get("since")
until      = st.session_state.get("until")
selected   = st.session_state.get("selected_campaigns", [])

if not account_id:
    st.warning("⚠️ Volte à página principal e selecione uma conta.")
    st.stop()

st.title("🗂️ Conjuntos de Anúncios")
st.caption(f"{since} → {until}")

with st.spinner("Buscando dados de conjuntos..."):
    try:
        df_raw, df_prev_raw, _, _ = get_adset_insights_with_comparison(account_id, since, until)
    except Exception as e:
        st.error(f"Erro ao buscar conjuntos: {e}")
        st.stop()

if df_raw.empty:
    st.warning("Nenhum dado de conjuntos encontrado para o período.")
    st.stop()

for _col in ("conversations", "cpc_conv"):
    if _col not in df_raw.columns:
        df_raw[_col] = 0
    if not df_prev_raw.empty and _col not in df_prev_raw.columns:
        df_prev_raw[_col] = 0

if selected:
    df = df_raw[df_raw["campaign_name"].isin(selected)].copy()
    df_prev = df_prev_raw[df_prev_raw["campaign_name"].isin(selected)].copy() if not df_prev_raw.empty else df_prev_raw
else:
    df = df_raw.copy()
    df_prev = df_prev_raw.copy()

if df.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

# ── Alertas (usa dados de campanha do cache + dados de conjunto) ────────────
try:
    df_camp, df_camp_prev, _, _ = get_insights_with_comparison(account_id, since, until)
    if selected:
        df_camp = df_camp[df_camp["campaign_name"].isin(selected)].copy()
        if not df_camp_prev.empty:
            df_camp_prev = df_camp_prev[df_camp_prev["campaign_name"].isin(selected)].copy()
except Exception:
    df_camp, df_camp_prev = df, df_prev

alerts = generate_alerts(df_camp, df_camp_prev, df_adsets=df)
if alerts:
    n_crit = sum(1 for a in alerts if a["level"] == "critical")
    label  = f"⚡ {len(alerts)} alertas e sugestões"
    if n_crit:
        label += f" · 🔴 {n_crit} crítico{'s' if n_crit > 1 else ''}"

    _level_style = {
        "critical": ("rgba(239,68,68,0.1)",    "#FCA5A5", "rgba(239,68,68,0.3)"),
        "warning":  ("rgba(245,158,11,0.1)",   "#FCD34D", "rgba(245,158,11,0.3)"),
        "positive": ("rgba(16,185,129,0.1)",   "#6EE7B7", "rgba(16,185,129,0.3)"),
        "info":     ("rgba(99,179,237,0.1)",   "#90CDF4", "rgba(99,179,237,0.3)"),
    }
    _level_icon = {"critical": "🔴", "warning": "🟡", "positive": "🟢", "info": "🔵"}

    with st.expander(label, expanded=n_crit > 0):
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

st.divider()

# ── KPIs globais ────────────────────────────────────────────────────────────
def _met(col_st, label, col_name, fmt_fn, lower=False, agg="sum"):
    cur = df[col_name].sum() if agg == "sum" else df[col_name].mean()
    prv = (df_prev[col_name].sum() if (not df_prev.empty and col_name in df_prev.columns and agg == "sum")
           else (df_prev[col_name].mean() if (not df_prev.empty and col_name in df_prev.columns) else 0))
    d, pos = delta_pct(cur, prv)
    if lower and pos is not None:
        pos = not pos
    col_st.metric(label, fmt_fn(cur), delta=d, delta_color="normal" if (pos is None or pos) else "inverse")

c1, c2, c3, c4, c5 = st.columns(5)
_met(c1, "💰 Investimento", "spend",       currency)
_met(c2, "👁️ Impressões",  "impressions",  number)
_met(c3, "🖱️ Cliques",     "clicks",       number)
_met(c4, "🎯 Leads",       "leads",        number)
_met(c5, "🛒 Compras",     "purchases",    number)

n_adsets = df["adset_id"].nunique() if "adset_id" in df.columns else len(df)
st.caption(f"**{n_adsets}** conjuntos · **{df['campaign_name'].nunique()}** campanhas")
st.divider()


# ── Helper: agrega e exibe tab de tipo ──────────────────────────────────────
def _render_tab(df_t, tab_type):
    if df_t.empty:
        st.info("Nenhum conjunto para este tipo no período.")
        return

    agg = df_t.groupby("adset_name").agg(
        campaign_name=("campaign_name", "first"),
        spend=("spend", "sum"), impressions=("impressions", "sum"),
        reach=("reach", "sum"), clicks=("clicks", "sum"),
        leads=("leads", "sum"), purchases=("purchases", "sum"),
        purchase_value=("purchase_value", "sum"),
        frequency=("frequency", "mean"),
        conversations=("conversations", "sum"),
    ).reset_index()

    agg["ctr"]  = agg.apply(lambda r: r["clicks"] / r["impressions"] * 100 if r["impressions"] > 0 else 0, axis=1)
    agg["cpc"]  = agg.apply(lambda r: r["spend"]  / r["clicks"]      if r["clicks"]      > 0 else 0, axis=1)
    agg["cpl"]  = agg.apply(lambda r: r["spend"]  / r["leads"]       if r["leads"]       > 0 else 0, axis=1)
    agg["cpa"]  = agg.apply(lambda r: r["spend"]  / r["purchases"]   if r["purchases"]   > 0 else 0, axis=1)
    agg["roas"] = agg.apply(lambda r: r["purchase_value"] / r["spend"] if r["spend"] > 0 else 0, axis=1)
    agg["cpm"]  = agg.apply(lambda r: r["spend"]  / r["impressions"] * 1000 if r["impressions"] > 0 else 0, axis=1)
    agg = agg.sort_values("spend", ascending=False)

    col_a, col_b = st.columns(2)

    with col_a:
        st.plotly_chart(
            charts.bar(agg.head(8).rename(columns={"adset_name": "Conjunto", "spend": "Investimento"}),
                       "Conjunto", "Investimento", "Top 8 por investimento", horizontal=True),
            use_container_width=True,
        )

    with col_b:
        if tab_type == "awareness" and agg["frequency"].sum() > 0:
            st.plotly_chart(
                charts.bar(agg.head(8).rename(columns={"adset_name": "Conjunto", "frequency": "Frequência"}),
                           "Conjunto", "Frequência", "Frequência por conjunto", horizontal=True, color=charts.ORANGE),
                use_container_width=True,
            )
        elif tab_type == "leads" and agg["cpl"].sum() > 0:
            best_cpl = agg[agg["cpl"] > 0].sort_values("cpl").head(8)
            st.plotly_chart(
                charts.bar(best_cpl.rename(columns={"adset_name": "Conjunto", "cpl": "CPL (R$)"}),
                           "Conjunto", "CPL (R$)", "Menor CPL (melhor desempenho)", horizontal=True, color=charts.GREEN),
                use_container_width=True,
            )
        elif tab_type == "conversions" and agg["roas"].sum() > 0:
            best_roas = agg[agg["roas"] > 0].sort_values("roas", ascending=False).head(8)
            st.plotly_chart(
                charts.bar(best_roas.rename(columns={"adset_name": "Conjunto", "roas": "ROAS"}),
                           "Conjunto", "ROAS", "ROAS por conjunto", horizontal=True, color=charts.GREEN),
                use_container_width=True,
            )
        else:
            best_ctr = agg[agg["ctr"] > 0].sort_values("ctr", ascending=False).head(8)
            if not best_ctr.empty:
                st.plotly_chart(
                    charts.bar(best_ctr.rename(columns={"adset_name": "Conjunto", "ctr": "CTR (%)"}),
                               "Conjunto", "CTR (%)", "Melhor CTR por conjunto", horizontal=True, color=charts.CYAN),
                    use_container_width=True,
                )

    # Tabela por tipo
    col_sets = {
        None:          ["adset_name", "campaign_name", "spend", "impressions", "clicks", "ctr", "cpc", "leads", "cpl", "purchases", "roas"],
        "awareness":   ["adset_name", "campaign_name", "spend", "reach", "impressions", "frequency", "cpm"],
        "traffic":     ["adset_name", "campaign_name", "spend", "clicks", "impressions", "ctr", "cpc"],
        "leads":       ["adset_name", "campaign_name", "spend", "leads", "cpl", "ctr", "impressions"],
        "conversions": ["adset_name", "campaign_name", "spend", "purchase_value", "roas", "purchases", "cpa"],
    }
    rename_map = {
        "adset_name": "Conjunto", "campaign_name": "Campanha",
        "spend": "Invest.", "impressions": "Impressões", "reach": "Alcance",
        "clicks": "Cliques", "ctr": "CTR %", "cpc": "CPC", "cpm": "CPM",
        "leads": "Leads", "cpl": "CPL", "purchases": "Compras",
        "purchase_value": "Receita", "roas": "ROAS", "cpa": "CPA", "frequency": "Freq.",
    }
    fmt_map = {
        "Invest.": currency, "CPM": currency, "CPC": currency,
        "CPL": currency, "CPA": currency, "Receita": currency,
        "CTR %": percent, "ROAS": lambda v: f"{v:.2f}x", "Freq.": lambda v: f"{v:.2f}x",
        "Impressões": number, "Alcance": number, "Cliques": number, "Leads": number, "Compras": number,
    }
    cols = col_sets.get(tab_type, col_sets[None])
    display = agg[[c for c in cols if c in agg.columns]].rename(columns=rename_map)
    st.dataframe(
        display.style.format({k: v for k, v in fmt_map.items() if k in display.columns}),
        use_container_width=True,
        height=420,
    )


# ── Tabs por tipo de campanha ───────────────────────────────────────────────
tabs = st.tabs(["Todos", "Awareness", "Tráfego", "Leads", "Conversões"])
type_map = [
    ("Todos",      None),
    ("Awareness",  "awareness"),
    ("Tráfego",    "traffic"),
    ("Leads",      "leads"),
    ("Conversões", "conversions"),
]

for tab, (label, ctype) in zip(tabs, type_map):
    with tab:
        df_t = df if ctype is None else df[df["campaign_type"] == ctype]
        _render_tab(df_t, ctype)

st.divider()

# ── Controles de conjunto ─────────────────────────────────────────────────────
STATUS_ICON = {"ACTIVE": "🟢", "PAUSED": "🟡", "WITH_ISSUES": "🔴"}
BUDGET_LABEL = {"daily": "Diário", "lifetime": "Vitalício"}

with st.expander("⚙️ Controles de Conjunto", expanded=False):
    col_hdr, col_btn = st.columns([6, 1])
    col_hdr.markdown("**Pausar, ativar ou ajustar orçamento por conjunto**")
    if col_btn.button("🔄 Atualizar", key="refresh_adsets", use_container_width=True):
        get_adsets_management.clear()
        get_campaigns_management.clear()
        st.rerun()

    with st.spinner("Carregando conjuntos..."):
        try:
            adsets_mgmt = get_adsets_management(account_id)
            camps_mgmt  = get_campaigns_management(account_id)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            st.stop()

    camp_budget = {
        c["id"]: int(c.get("daily_budget") or 0) + int(c.get("lifetime_budget") or 0)
        for c in camps_mgmt
    }

    def _adset_budget(a):
        db = int(a.get("daily_budget") or 0)
        lb = int(a.get("lifetime_budget") or 0)
        if db > 0:
            return "daily", db / 100
        if lb > 0:
            return "lifetime", lb / 100
        return "abo", None

    if selected:
        camp_ids = {c["id"] for c in camps_mgmt if c["name"] in selected}
        adsets_mgmt = [a for a in adsets_mgmt if a.get("campaign_id") in camp_ids]

    if not adsets_mgmt:
        st.info("Nenhum conjunto encontrado.")
    else:
        adset_labels = [
            f"{STATUS_ICON.get(a['status'], '⚪')} {a['name']}" for a in adsets_mgmt
        ]
        sel_adset_idx = st.selectbox(
            "Selecione o conjunto",
            range(len(adset_labels)),
            format_func=lambda i: adset_labels[i],
            key="adset_sel",
        )

        if st.session_state.get("_last_adset_sel") != sel_adset_idx:
            st.session_state.pop("_adset_confirm_status", None)
            st.session_state.pop("_adset_confirm_budget", None)
            st.session_state["_last_adset_sel"] = sel_adset_idx

        a = adsets_mgmt[sel_adset_idx]
        btype, bval = _adset_budget(a)
        is_cbo = camp_budget.get(a.get("campaign_id"), 0) > 0

        col_info, col_act = st.columns([3, 2])
        with col_info:
            st.markdown(f"**Conjunto:** {a['name']}")
            st.markdown(f"**Status:** {STATUS_ICON.get(a['status'], '⚪')} `{a['status']}`")
            if is_cbo:
                st.markdown("**Orçamento:** Controlado pela campanha (CBO)")
            elif bval:
                st.markdown(f"**Orçamento {BUDGET_LABEL.get(btype, '')}:** {currency(bval)}")
            else:
                st.markdown("**Orçamento:** Não definido")

        with col_act:
            if a["status"] == "ACTIVE":
                if st.button("⏸️ Pausar conjunto", type="primary", use_container_width=True, key="adset_pause"):
                    st.session_state["_adset_confirm_status"] = {"id": a["id"], "name": a["name"], "new_status": "PAUSED"}
            else:
                if st.button("▶️ Ativar conjunto", type="primary", use_container_width=True, key="adset_activate"):
                    st.session_state["_adset_confirm_status"] = {"id": a["id"], "name": a["name"], "new_status": "ACTIVE"}

        if "_adset_confirm_status" in st.session_state:
            cs = st.session_state["_adset_confirm_status"]
            action = "pausar" if cs["new_status"] == "PAUSED" else "ativar"
            st.warning(f"Confirma **{action}** o conjunto **{cs['name']}**?")
            c1, c2, _ = st.columns([1, 1, 3])
            if c1.button("✅ Confirmar", key="adset_yes_status"):
                try:
                    update_status(cs["id"], cs["new_status"])
                    st.success(f"Conjunto {'pausado' if cs['new_status'] == 'PAUSED' else 'ativado'} com sucesso!")
                    st.session_state.pop("_adset_confirm_status", None)
                    get_adsets_management.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
            if c2.button("❌ Cancelar", key="adset_no_status"):
                st.session_state.pop("_adset_confirm_status", None)
                st.rerun()

        if not is_cbo and bval is not None:
            st.markdown(f"**Alterar orçamento {BUDGET_LABEL.get(btype, '')}**")
            new_bval = st.number_input(
                "Novo valor (R$)", min_value=1.0, value=float(bval),
                step=1.0, format="%.2f", key="adset_budget_input",
            )
            if st.button("💾 Salvar orçamento", key="adset_save_budget"):
                st.session_state["_adset_confirm_budget"] = {
                    "id": a["id"], "name": a["name"], "budget_type": btype, "value": new_bval,
                }

            if "_adset_confirm_budget" in st.session_state:
                cb = st.session_state["_adset_confirm_budget"]
                st.warning(f"Confirma alterar orçamento de **{cb['name']}** para **{currency(cb['value'])}**?")
                c1, c2, _ = st.columns([1, 1, 3])
                if c1.button("✅ Confirmar", key="adset_yes_budget"):
                    try:
                        kwargs = (
                            {"daily_budget": cb["value"]}
                            if cb["budget_type"] == "daily"
                            else {"lifetime_budget": cb["value"]}
                        )
                        update_budget(cb["id"], **kwargs)
                        st.success("Orçamento atualizado com sucesso!")
                        st.session_state.pop("_adset_confirm_budget", None)
                        get_adsets_management.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                if c2.button("❌ Cancelar", key="adset_no_budget"):
                    st.session_state.pop("_adset_confirm_budget", None)
                    st.rerun()
        elif is_cbo:
            st.info("Orçamento controlado pela campanha (CBO). Ajuste na página **Gestão de Campanhas**.")
