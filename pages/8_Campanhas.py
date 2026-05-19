import streamlit as st
import pandas as pd
from utils.meta_api import (
    get_campaigns_management, update_status, update_budget, OBJECTIVE_MAP
)
from utils.formatters import currency
from utils.styles import css

st.set_page_config(page_title="Gestão de Campanhas | Meta Ads", page_icon="⚙️", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

from utils.client_guard import redirect_if_client
redirect_if_client()

account_id = st.session_state.get("account_id")
if not account_id:
    st.warning("⚠️ Volte à página principal e selecione uma conta.")
    st.stop()

STATUS_ICON = {"ACTIVE": "🟢", "PAUSED": "🟡", "WITH_ISSUES": "🔴"}
BUDGET_LABEL = {"daily": "Diário", "lifetime": "Vitalício"}


def _budget_info(c):
    db = int(c.get("daily_budget") or 0)
    lb = int(c.get("lifetime_budget") or 0)
    if db > 0:
        return "daily", db / 100
    if lb > 0:
        return "lifetime", lb / 100
    return "abo", None


def _load_campaigns():
    return get_campaigns_management(account_id)


def _refresh():
    get_campaigns_management.clear()
    st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([6, 1])
col_title.title("⚙️ Gestão de Campanhas")
if col_btn.button("🔄 Atualizar", use_container_width=True):
    _refresh()

with st.spinner("Carregando campanhas..."):
    try:
        campaigns = _load_campaigns()
    except Exception as e:
        st.error(f"Erro ao carregar campanhas: {e}")
        st.stop()

if not campaigns:
    st.info("Nenhuma campanha ativa ou pausada encontrada.")
    st.stop()

# ── Tabela resumo ─────────────────────────────────────────────────────────────
rows = []
for c in campaigns:
    btype, bval = _budget_info(c)
    rows.append({
        "id": c["id"],
        "name": c["name"],
        "status": c["status"],
        "objective": OBJECTIVE_MAP.get(c.get("objective", ""), c.get("objective", "—")),
        "budget_type": btype,
        "budget_val": bval,
    })

df = pd.DataFrame(rows)

display = df.copy()
display["Status"] = display["status"].map(lambda s: f"{STATUS_ICON.get(s, '⚪')} {s}")
display["Orçamento"] = display.apply(
    lambda r: f"{BUDGET_LABEL.get(r['budget_type'], 'ABO')} — {currency(r['budget_val'])}"
    if r["budget_val"] else "Por conjunto (ABO)",
    axis=1,
)

st.dataframe(
    display[["name", "Status", "objective", "Orçamento"]].rename(columns={
        "name": "Campanha", "objective": "Objetivo"
    }),
    use_container_width=True,
    height=280,
    hide_index=True,
)

st.divider()

# ── Painel de gestão ──────────────────────────────────────────────────────────
st.subheader("Gerenciar campanha")

camp_labels = [f"{STATUS_ICON.get(r['status'], '⚪')} {r['name']}" for _, r in df.iterrows()]
sel_idx = st.selectbox("Selecione a campanha", range(len(camp_labels)), format_func=lambda i: camp_labels[i], key="camp_sel")

if sel_idx is not None:
    row = df.iloc[sel_idx]

    # Clear confirmations when selection changes
    if st.session_state.get("_last_camp_sel") != sel_idx:
        st.session_state.pop("_confirm_status", None)
        st.session_state.pop("_confirm_budget", None)
        st.session_state["_last_camp_sel"] = sel_idx

    col_info, col_act = st.columns([3, 2])

    with col_info:
        st.markdown(f"**Campanha:** {row['name']}")
        st.markdown(f"**Status:** {STATUS_ICON.get(row['status'], '⚪')} `{row['status']}`")
        st.markdown(f"**Objetivo:** {row['objective']}")
        if row["budget_val"]:
            st.markdown(f"**Orçamento {BUDGET_LABEL.get(row['budget_type'], '')}:** {currency(row['budget_val'])}")
        else:
            st.markdown("**Orçamento:** Definido por conjunto (ABO)")

    with col_act:
        if row["status"] == "ACTIVE":
            if st.button("⏸️ Pausar campanha", type="primary", use_container_width=True, key="btn_pause"):
                st.session_state["_confirm_status"] = {"id": row["id"], "name": row["name"], "new_status": "PAUSED"}
        else:
            if st.button("▶️ Ativar campanha", type="primary", use_container_width=True, key="btn_activate"):
                st.session_state["_confirm_status"] = {"id": row["id"], "name": row["name"], "new_status": "ACTIVE"}

    # Confirmação de status
    if "_confirm_status" in st.session_state:
        cs = st.session_state["_confirm_status"]
        action = "pausar" if cs["new_status"] == "PAUSED" else "ativar"
        st.warning(f"Confirma **{action}** a campanha **{cs['name']}**?")
        c1, c2, _ = st.columns([1, 1, 3])
        if c1.button("✅ Confirmar", key="yes_status"):
            try:
                update_status(cs["id"], cs["new_status"])
                st.success(f"Campanha {'pausada' if cs['new_status'] == 'PAUSED' else 'ativada'} com sucesso!")
                st.session_state.pop("_confirm_status", None)
                _refresh()
            except Exception as e:
                st.error(f"Erro: {e}")
        if c2.button("❌ Cancelar", key="no_status"):
            st.session_state.pop("_confirm_status", None)
            st.rerun()

    # Edição de orçamento (apenas CBO)
    if row["budget_val"] is not None:
        st.divider()
        st.markdown(f"**Alterar orçamento {BUDGET_LABEL.get(row['budget_type'], '')}**")
        new_budget = st.number_input(
            "Novo valor (R$)",
            min_value=1.0,
            value=float(row["budget_val"]),
            step=1.0,
            format="%.2f",
            key="budget_input",
        )
        if st.button("💾 Salvar orçamento", key="btn_save_budget"):
            st.session_state["_confirm_budget"] = {
                "id": row["id"], "name": row["name"],
                "budget_type": row["budget_type"], "value": new_budget,
            }

        if "_confirm_budget" in st.session_state:
            cb = st.session_state["_confirm_budget"]
            st.warning(
                f"Confirma alterar o orçamento de **{cb['name']}** "
                f"para **{currency(cb['value'])}**?"
            )
            c1, c2, _ = st.columns([1, 1, 3])
            if c1.button("✅ Confirmar", key="yes_budget"):
                try:
                    kwargs = (
                        {"daily_budget": cb["value"]}
                        if cb["budget_type"] == "daily"
                        else {"lifetime_budget": cb["value"]}
                    )
                    update_budget(cb["id"], **kwargs)
                    st.success("Orçamento atualizado com sucesso!")
                    st.session_state.pop("_confirm_budget", None)
                    _refresh()
                except Exception as e:
                    st.error(f"Erro: {e}")
            if c2.button("❌ Cancelar", key="no_budget"):
                st.session_state.pop("_confirm_budget", None)
                st.rerun()
    else:
        st.info("Orçamento definido por conjunto (ABO). Ajuste na página **Conjuntos de Anúncios**.")
