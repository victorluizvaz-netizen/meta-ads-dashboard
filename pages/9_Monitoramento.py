import secrets
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.styles import css, section_header
from utils.whatsapp import send_message
from utils.config_loader import load_config, save_config as _save_config

st.set_page_config(page_title="Monitoramento | Meta Ads", page_icon="📱", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

from utils.client_guard import redirect_if_client
redirect_if_client()

LOG_PATH = Path(__file__).parent.parent / "alertas_log.json"


def _load_config() -> dict:
    return load_config()


@st.cache_data(ttl=15)
def _load_log() -> dict:
    if LOG_PATH.exists():
        with open(LOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _whatsapps_for(account: dict) -> list:
    if "whatsapps" in account and account["whatsapps"]:
        return list(account["whatsapps"])
    if account.get("whatsapp"):
        return [account["whatsapp"]]
    return []


def _fmt_number(n: str) -> str:
    n = n.strip()
    if len(n) == 13:
        return f"+{n[:2]} {n[2:4]} {n[4:9]}-{n[9:]}"
    if len(n) == 12:
        return f"+{n[:2]} {n[2:4]} {n[4:8]}-{n[8:]}"
    return n


# ── Page header ────────────────────────────────────────────────────────────────
st.title("📱 Monitoramento de Leads & Conversas")
st.caption(
    "Configure alertas em tempo real por conta de anúncio. "
    "Os alertas são enviados pelo runner a cada execução do Windows Task Scheduler."
)

cfg = _load_config()
if not cfg:
    st.error(
        "`config_alertas.json` não encontrado. "
        "Certifique-se de que o arquivo existe na raiz do projeto."
    )
    st.stop()

log       = _load_log()
snap_all  = log.get("leads_snapshot", {})
today_str = datetime.now().strftime("%Y-%m-%d")
contas    = cfg.get("contas", [])
evo       = cfg.get("evolution_api", {})
public_url = cfg.get("public_url", "").rstrip("/")

# ── Status global ──────────────────────────────────────────────────────────────
n_leads = sum(1 for c in contas if c.get("monitor_leads"))
n_conv  = sum(1 for c in contas if c.get("monitor_conversations"))
st.markdown(
    section_header("Status geral", f"{n_leads} conta(s) monitorando leads · {n_conv} conta(s) monitorando conversas"),
    unsafe_allow_html=True,
)

# Última execução do runner (ts mais recente nos snapshots de hoje)
last_run_ts = None
for aid, s in snap_all.items():
    if s.get("date") == today_str:
        ts = s.get("ts", "")
        if ts and (last_run_ts is None or ts > last_run_ts):
            last_run_ts = ts

if last_run_ts:
    try:
        dt_last = datetime.fromisoformat(last_run_ts)
        diff_min = int((datetime.now() - dt_last).total_seconds() / 60)
        diff_txt = f"há {diff_min} min" if diff_min < 60 else f"há {diff_min // 60}h {diff_min % 60}min"
        st.info(f"⏱️ Última execução do runner: **{dt_last.strftime('%H:%M')}** ({diff_txt})")
    except Exception:
        pass
else:
    st.warning("⏱️ Nenhuma execução de monitoramento registrada hoje. Verifique o Task Scheduler.")

st.divider()

# ── Cards por conta ────────────────────────────────────────────────────────────
for idx, account in enumerate(contas):
    account_id = account["account_id"]
    label      = account.get("label", account_id)

    # Session state para números desta conta
    nums_key = f"_mon_nums_{account_id}"
    if nums_key not in st.session_state:
        st.session_state[nums_key] = _whatsapps_for(account)

    # Snapshot de hoje para esta conta
    acct_snap   = snap_all.get(account_id, {})
    snap_today  = acct_snap.get("date") == today_str
    leads_hoje  = sum(acct_snap.get("leads", {}).values())        if snap_today else 0
    conv_hoje   = sum(acct_snap.get("conversations", {}).values()) if snap_today else 0
    last_check  = acct_snap.get("ts") if snap_today else None

    is_active = account.get("monitor_leads") or account.get("monitor_conversations")

    # ── Card header ─────────────────────────────────────────────────────────────
    badge_html = (
        '<span style="background:rgba(74,222,128,0.12);color:#86EFAC;border:1px solid rgba(74,222,128,0.3);'
        'padding:0.2rem 0.6rem;border-radius:20px;font-size:0.75rem;font-weight:600;">🟢 ATIVO</span>'
        if is_active else
        '<span style="background:rgba(100,100,100,0.12);color:#94A3B8;border:1px solid rgba(100,100,100,0.2);'
        'padding:0.2rem 0.6rem;border-radius:20px;font-size:0.75rem;font-weight:600;">⚫ INATIVO</span>'
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.2rem;">'
        f'<span style="font-size:1.1rem;font-weight:700;color:#F1ECF8;">{label}</span>'
        f'{badge_html}</div>'
        f'<div style="color:#5B4E7A;font-size:0.8rem;margin-bottom:1rem;font-family:monospace;">{account_id}</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1, 1], gap="large")

    # ── Toggles ──────────────────────────────────────────────────────────────────
    with col_left:
        st.markdown("**Monitoramento ativo**")
        mon_leads = st.toggle(
            "🎯 Novos leads",
            value=account.get("monitor_leads", False),
            key=f"tog_leads_{account_id}",
            help="Envia alerta no WhatsApp a cada novo lead gerado hoje",
        )
        mon_conv = st.toggle(
            "💬 Novas conversas",
            value=account.get("monitor_conversations", False),
            key=f"tog_conv_{account_id}",
            help="Envia alerta no WhatsApp a cada nova conversa iniciada hoje",
        )
        st.markdown("")

        if last_check:
            try:
                dt_c = datetime.fromisoformat(last_check)
                st.caption(f"⏱️ Último check: **{dt_c.strftime('%H:%M')}**")
            except Exception:
                pass
        if snap_today:
            st.caption(f"📊 Snapshot hoje: **{int(leads_hoje)}** leads · **{int(conv_hoje)}** conversas")
        else:
            st.caption("📊 Sem snapshot para hoje ainda")

    # ── Números WhatsApp ─────────────────────────────────────────────────────────
    with col_right:
        st.markdown("**WhatsApp para alertas**")
        nums = st.session_state[nums_key]

        if nums:
            for i, num in enumerate(nums):
                c_num, c_del = st.columns([5, 1])
                c_num.markdown(
                    f'<div style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.18);'
                    f'border-radius:8px;padding:0.4rem 0.9rem;font-size:0.84rem;color:#D4B0FF;'
                    f'font-family:monospace;margin-bottom:4px;">📱 {_fmt_number(num)}</div>',
                    unsafe_allow_html=True,
                )
                if c_del.button("✕", key=f"del_{account_id}_{i}", help="Remover número"):
                    st.session_state[nums_key].pop(i)
                    st.rerun()
        else:
            st.caption("Nenhum número cadastrado.")

        # Input para adicionar número
        c_inp, c_add = st.columns([4, 1])
        new_num = c_inp.text_input(
            "Novo número",
            placeholder="5549999999999",
            label_visibility="collapsed",
            key=f"new_num_{account_id}",
        )
        if c_add.button("＋", key=f"add_{account_id}", use_container_width=True, help="Adicionar número"):
            cleaned = new_num.strip().replace("+", "").replace(" ", "").replace("-", "")
            if cleaned.isdigit() and len(cleaned) >= 10:
                if cleaned not in st.session_state[nums_key]:
                    st.session_state[nums_key].append(cleaned)
                    st.rerun()
                else:
                    st.warning("Número já cadastrado.")
            else:
                st.error("Inválido. Use apenas dígitos no formato internacional, ex: `5549999999999`")

    # ── Botões salvar / testar ───────────────────────────────────────────────────
    st.markdown("")
    col_save, col_test, _spc = st.columns([1, 1, 4])

    if col_save.button("💾 Salvar", key=f"save_{account_id}", type="primary", use_container_width=True):
        cfg["contas"][idx]["monitor_leads"]         = bool(st.session_state.get(f"tog_leads_{account_id}", False))
        cfg["contas"][idx]["monitor_conversations"] = bool(st.session_state.get(f"tog_conv_{account_id}", False))
        nums_to_save = list(st.session_state[nums_key])
        cfg["contas"][idx]["whatsapps"] = nums_to_save
        cfg["contas"][idx]["whatsapp"]  = nums_to_save[0] if nums_to_save else ""
        _save_config(cfg)
        _load_log.clear()
        st.success(f"✅ **{label}** salvo!")
        st.rerun()

    if col_test.button("📲 Testar", key=f"test_{account_id}", use_container_width=True):
        if not evo.get("base_url"):
            st.error("Evolution API não configurada em `config_alertas.json`.")
        elif not st.session_state[nums_key]:
            st.error("Nenhum número cadastrado para enviar o teste.")
        else:
            tipos = []
            if st.session_state.get(f"tog_leads_{account_id}"):  tipos.append("🎯 Leads")
            if st.session_state.get(f"tog_conv_{account_id}"):   tipos.append("💬 Conversas")
            tipo_txt = " · ".join(tipos) if tipos else "Nenhum (monitoramento desativado)"
            test_msg = (
                f"✅ *Teste de alerta — Meta Ads Dashboard*\n"
                f"Conta: _{label}_\n"
                f"Monitoramento: {tipo_txt}\n"
                f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            failed, success = [], 0
            for num in st.session_state[nums_key]:
                ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], num, test_msg)
                if ok:
                    success += 1
                else:
                    failed.append(_fmt_number(num))
            if success:
                st.success(f"📲 Mensagem enviada para {success} número(s)!")
            if failed:
                st.error(f"Falha ao enviar para: {', '.join(failed)}")

    # ── Acesso de cliente ────────────────────────────────────────────────────────
    st.markdown(section_header("Acesso de cliente", "link exclusivo de visualização — sem acesso a outras contas"), unsafe_allow_html=True)

    client_token = account.get("client_token", "")

    if client_token:
        if not public_url:
            st.warning("⚠️ Configure `public_url` no `config_alertas.json` para gerar o link correto.")
            client_url = None
        else:
            client_url = f"{public_url}/Cliente?token={client_token}"

        if client_url:
            st.markdown(
                f'<div style="background:rgba(168,85,247,0.07);border:1px solid rgba(168,85,247,0.20);'
                f'border-radius:10px;padding:0.7rem 1rem;margin:0.4rem 0;">'
                f'<div style="color:#8B7EAF;font-size:0.70rem;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.08em;margin-bottom:0.35rem;">🔗 Link ativo</div>'
                f'<code style="color:#C084FC;font-size:0.83rem;word-break:break-all;">{client_url}</code>'
                f'</div>',
                unsafe_allow_html=True,
            )
        col_regen, col_revoke, _spc = st.columns([1, 1, 4])
        if col_regen.button("🔄 Regenerar", key=f"regen_{account_id}", use_container_width=True,
                            help="Gera um novo token — o link anterior deixa de funcionar"):
            cfg["contas"][idx]["client_token"] = secrets.token_urlsafe(8)
            _save_config(cfg)
            st.success("Novo link gerado. O link anterior foi invalidado.")
            st.rerun()
        if col_revoke.button("🗑️ Revogar", key=f"revoke_{account_id}", use_container_width=True,
                             help="Remove o acesso — o link atual deixa de funcionar"):
            cfg["contas"][idx]["client_token"] = ""
            _save_config(cfg)
            st.success("Acesso revogado.")
            st.rerun()
    else:
        st.caption("Nenhum link ativo para esta conta.")
        col_gen, _spc = st.columns([2, 4])
        if col_gen.button("🔗 Gerar link de acesso", key=f"gen_{account_id}", use_container_width=True):
            cfg["contas"][idx]["client_token"] = secrets.token_urlsafe(8)
            _save_config(cfg)
            st.success("Link gerado! Copie o endereço acima e compartilhe com o cliente.")
            st.rerun()

    st.divider()

st.caption(
    "⚙️ O runner `alertas_runner.py` verifica novos leads a cada execução do Task Scheduler. "
    "Recomendado: a cada 15 minutos entre 06:00 e 23:00."
)

# ── Histórico de performance ───────────────────────────────────────────────────
history_all = log.get("history", {})
if history_all:
    st.markdown(
        section_header("Histórico de performance", "evolução diária registrada pelo runner"),
        unsafe_allow_html=True,
    )
    acct_options = {a.get("label", a["account_id"]): a["account_id"] for a in contas}
    sel_label = st.selectbox("Conta", list(acct_options.keys()), key="hist_acct")
    sel_id    = acct_options[sel_label]
    hist      = history_all.get(sel_id, {})

    if hist:
        df_h = pd.DataFrame([
            {"data": k, **v} for k, v in sorted(hist.items())
        ])
        df_h["data"] = pd.to_datetime(df_h["data"])

        metric = st.radio("Métrica", ["spend", "leads", "conversations", "cpl"],
                          format_func=lambda x: {"spend": "Investimento (R$)", "leads": "Leads",
                                                  "conversations": "Conversas", "cpl": "CPL (R$)"}[x],
                          horizontal=True, key="hist_metric")

        df_plot = df_h.dropna(subset=[metric])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_plot["data"], y=df_plot[metric],
            mode="lines+markers",
            line=dict(color="#A855F7", width=2),
            marker=dict(color="#EC4899", size=6),
            fill="tozeroy",
            fillcolor="rgba(168,85,247,0.08)",
            hovertemplate="%{x|%d/%m}<br>%{y:.2f}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=220,
            xaxis=dict(showgrid=False, color="#7B6EA8"),
            yaxis=dict(gridcolor="#1C1236", color="#7B6EA8"),
            font=dict(color="#D4B0FF"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"{len(df_h)} dias registrados | último: {df_h['data'].max().strftime('%d/%m/%Y')}")
    else:
        st.caption("Nenhum dado histórico ainda para esta conta. O runner irá registrar a partir do próximo ciclo.")
