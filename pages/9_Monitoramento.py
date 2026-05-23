import json
import secrets
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.styles import css, section_header
from utils.whatsapp import send_message, send_document, list_groups
from utils.config_loader import load_config, save_config as _save_config
from utils.tz import now_br

st.set_page_config(page_title="Monitoramento | Meta Ads", page_icon="📡", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

# ── Estilos específicos desta página ────────────────────────────────────────────
st.markdown("""
<style>
/* Cards de conta via st.container(border=True) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(155deg, #0A1020 0%, #060D1A 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.14) !important;
    border-radius: 20px !important;
    box-shadow: 0 2px 28px rgba(0,0,0,0.50), inset 0 1px 0 rgba(255,255,255,0.025) !important;
    padding: 0.2rem 0.4rem !important;
    margin-bottom: 0.6rem !important;
}
/* Labels dos toggles */
div[data-testid="stToggle"] label p {
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #93C5FD !important;
}
/* Caption text mais escuro */
.stCaption p { color: #5B4E7A !important; font-size: 0.77rem !important; }
</style>
""", unsafe_allow_html=True)

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


def _is_group(n: str) -> bool:
    return "@g.us" in n


def _fmt_number(n: str) -> str:
    n = n.strip()
    if _is_group(n):
        return n
    if len(n) == 13:
        return f"+{n[:2]} {n[2:4]} {n[4:9]}-{n[9:]}"
    if len(n) == 12:
        return f"+{n[:2]} {n[2:4]} {n[4:8]}-{n[8:]}"
    return n


def _label(text: str) -> str:
    return (
        f'<span style="font-size:0.67rem;font-weight:700;letter-spacing:0.10em;'
        f'text-transform:uppercase;color:#1A3A5C;display:block;margin-bottom:0.65rem;">'
        f'{text}</span>'
    )


# ── Cabeçalho da página ─────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.4rem;">
  <div style="font-size:1.55rem;font-weight:800;letter-spacing:-0.03em;
              background:linear-gradient(90deg,#F1ECF8 20%,#7DD3FC 100%);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text;line-height:1.2;margin-bottom:0.3rem;">
    Monitoramento
  </div>
  <div style="color:#5B4E7A;font-size:0.81rem;">
    Alertas em tempo real por conta · runner via Windows Task Scheduler
  </div>
</div>
""", unsafe_allow_html=True)

cfg = _load_config()
if not cfg:
    st.error("`config_alertas.json` não encontrado. Certifique-se de que o arquivo existe na raiz do projeto.")
    st.stop()

log        = _load_log()
snap_all   = log.get("leads_snapshot", {})
today_str  = now_br().strftime("%Y-%m-%d")
contas     = cfg.get("contas", [])
evo        = cfg.get("evolution_api", {})
public_url = cfg.get("public_url", "").rstrip("/")

# ── Barra de status ─────────────────────────────────────────────────────────────
n_leads = sum(1 for c in contas if c.get("monitor_leads"))
n_conv  = sum(1 for c in contas if c.get("monitor_conversations"))

last_run_ts = None
for aid, s in snap_all.items():
    if s.get("date") == today_str:
        ts = s.get("ts", "")
        if ts and (last_run_ts is None or ts > last_run_ts):
            last_run_ts = ts

if last_run_ts:
    try:
        dt_last  = datetime.fromisoformat(last_run_ts)
        diff_min = int((now_br() - dt_last).total_seconds() / 60)
        diff_txt = f"há {diff_min} min" if diff_min < 60 else f"há {diff_min // 60}h {diff_min % 60}min"
        runner_pill = (
            f'<span style="display:inline-flex;align-items:center;gap:0.45rem;'
            f'background:rgba(74,222,128,0.09);border:1px solid rgba(74,222,128,0.22);'
            f'border-radius:20px;padding:0.22rem 0.8rem;font-size:0.78rem;'
            f'color:#86EFAC;font-weight:500;">'
            f'<span style="width:6px;height:6px;border-radius:50%;background:#4ADE80;'
            f'display:inline-block;box-shadow:0 0 6px rgba(74,222,128,0.55);flex-shrink:0;"></span>'
            f'Runner · {dt_last.strftime("%H:%M")}'
            f'<span style="color:#4A7A60;font-weight:400;">({diff_txt})</span></span>'
        )
    except Exception:
        runner_pill = ""
else:
    runner_pill = (
        '<span style="display:inline-flex;align-items:center;gap:0.45rem;'
        'background:rgba(245,158,11,0.09);border:1px solid rgba(245,158,11,0.22);'
        'border-radius:20px;padding:0.22rem 0.8rem;font-size:0.78rem;'
        'color:#FCD34D;font-weight:500;">'
        '<span style="width:6px;height:6px;border-radius:50%;background:#F59E0B;'
        'display:inline-block;flex-shrink:0;"></span>'
        'Sem execução hoje — verifique o Task Scheduler</span>'
    )

pl = f'{n_leads} conta{"s" if n_leads != 1 else ""} · leads'
pc = f'{n_conv} conta{"s" if n_conv != 1 else ""} · conversas'
leads_pill = (
    f'<span style="background:rgba(56,189,248,0.10);border:1px solid rgba(56,189,248,0.22);'
    f'border-radius:20px;padding:0.22rem 0.8rem;font-size:0.78rem;color:#7DD3FC;font-weight:500;">{pl}</span>'
)
conv_pill = (
    f'<span style="background:rgba(245,158,11,0.09);border:1px solid rgba(245,158,11,0.22);'
    f'border-radius:20px;padding:0.22rem 0.8rem;font-size:0.78rem;color:#FCD34D;font-weight:500;">{pc}</span>'
)
st.markdown(
    f'<div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;margin-bottom:1.6rem;">'
    f'{runner_pill}{leads_pill}{conv_pill}</div>',
    unsafe_allow_html=True,
)

# ── Cards por conta ─────────────────────────────────────────────────────────────
for idx, account in enumerate(contas):
    account_id = account["account_id"]
    label      = account.get("label", account_id)

    nums_key = f"_mon_nums_{account_id}"
    if nums_key not in st.session_state:
        st.session_state[nums_key] = _whatsapps_for(account)

    acct_snap  = snap_all.get(account_id, {})
    snap_today = acct_snap.get("date") == today_str
    leads_hoje = sum(acct_snap.get("leads", {}).values())         if snap_today else 0
    conv_hoje  = sum(acct_snap.get("conversations", {}).values()) if snap_today else 0
    last_check = acct_snap.get("ts") if snap_today else None

    is_active = account.get("monitor_leads") or account.get("monitor_conversations")

    with st.container(border=True):

        # ── Cabeçalho do card ────────────────────────────────────────────────────
        dot_c  = '#4ADE80' if is_active else '#4B5563'
        txt_c  = '#86EFAC' if is_active else '#6B7280'
        bg_c   = 'rgba(74,222,128,0.09)' if is_active else 'rgba(75,85,99,0.14)'
        bd_c   = 'rgba(74,222,128,0.22)' if is_active else 'rgba(75,85,99,0.24)'
        badge  = 'ATIVO' if is_active else 'INATIVO'

        stat_chips = ""
        if snap_today:
            if leads_hoje > 0:
                stat_chips += (
                    f'<span style="background:rgba(56,189,248,0.10);border:1px solid rgba(56,189,248,0.20);'
                    f'border-radius:12px;padding:0.12rem 0.6rem;font-size:0.71rem;'
                    f'color:#7DD3FC;font-weight:600;">{int(leads_hoje)} leads</span> '
                )
            if conv_hoje > 0:
                stat_chips += (
                    f'<span style="background:rgba(245,158,11,0.09);border:1px solid rgba(245,158,11,0.20);'
                    f'border-radius:12px;padding:0.12rem 0.6rem;font-size:0.71rem;'
                    f'color:#FCD34D;font-weight:600;">{int(conv_hoje)} conversas</span>'
                )

        check_html = ""
        if last_check:
            try:
                dt_c_val = datetime.fromisoformat(last_check)
                check_html = (
                    f'<span style="color:#1E3A5A;font-size:0.72rem;">'
                    f'check {dt_c_val.strftime("%H:%M")}</span>'
                )
            except Exception:
                pass

        st.markdown(
            f'<div style="display:flex;align-items:flex-start;justify-content:space-between;'
            f'margin-bottom:1.1rem;flex-wrap:wrap;gap:0.5rem;">'
            f'  <div>'
            f'    <div style="display:flex;align-items:center;gap:0.55rem;margin-bottom:0.25rem;">'
            f'      <span style="font-size:1.05rem;font-weight:700;color:#F1ECF8;'
            f'             letter-spacing:-0.02em;">{label}</span>'
            f'      <span style="display:inline-flex;align-items:center;gap:0.35rem;'
            f'             background:{bg_c};border:1px solid {bd_c};'
            f'             border-radius:20px;padding:0.14rem 0.58rem;'
            f'             font-size:0.68rem;color:{txt_c};font-weight:700;letter-spacing:0.07em;">'
            f'        <span style="width:5px;height:5px;border-radius:50%;background:{dot_c};'
            f'               display:inline-block;flex-shrink:0;"></span>{badge}</span>'
            f'    </div>'
            f'    <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
            f'      <span style="color:#1E3A5A;font-size:0.74rem;'
            f'             font-family:monospace;">{account_id}</span>'
            f'      {check_html}'
            f'    </div>'
            f'  </div>'
            f'  <div style="display:flex;gap:0.35rem;align-items:center;'
            f'       flex-wrap:wrap;padding-top:0.1rem;">{stat_chips}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_left, col_right = st.columns([1, 1], gap="large")

        # ── Esquerda: toggles ────────────────────────────────────────────────────
        with col_left:
            st.markdown(_label("Monitoramento"), unsafe_allow_html=True)
            st.toggle(
                "Novos leads",
                value=account.get("monitor_leads", False),
                key=f"tog_leads_{account_id}",
                help="Envia alerta no WhatsApp a cada novo lead gerado hoje",
            )
            st.toggle(
                "Novas conversas",
                value=account.get("monitor_conversations", False),
                key=f"tog_conv_{account_id}",
                help="Envia alerta no WhatsApp a cada nova conversa iniciada hoje",
            )

        # ── Direita: destinatários ───────────────────────────────────────────────
        with col_right:
            st.markdown(_label("Destinatários WhatsApp"), unsafe_allow_html=True)
            nums = st.session_state[nums_key]

            if nums:
                for i, num in enumerate(nums):
                    c_num, c_del = st.columns([5, 1])
                    is_grp   = _is_group(num)
                    chip_bg  = 'rgba(245,158,11,0.07)' if is_grp else 'rgba(56,189,248,0.07)'
                    chip_bd  = 'rgba(245,158,11,0.19)' if is_grp else 'rgba(56,189,248,0.17)'
                    chip_clr = '#FCD34D' if is_grp else '#93C5FD'
                    type_lbl = (
                        '<span style="opacity:0.45;font-size:0.70rem;margin-right:0.3rem;'
                        'font-style:italic;">grupo</span>'
                        if is_grp else ""
                    )
                    c_num.markdown(
                        f'<div style="background:{chip_bg};border:1px solid {chip_bd};'
                        f'border-radius:8px;padding:0.36rem 0.85rem;font-size:0.81rem;'
                        f'color:{chip_clr};font-family:monospace;margin-bottom:4px;'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                        f'{type_lbl}{_fmt_number(num)}</div>',
                        unsafe_allow_html=True,
                    )
                    if c_del.button("✕", key=f"del_{account_id}_{i}", help="Remover"):
                        st.session_state[nums_key].pop(i)
                        st.rerun()
            else:
                st.markdown(
                    '<div style="color:#1E3A5A;font-size:0.82rem;padding:0.4rem 0;">'
                    'Nenhum destinatário cadastrado</div>',
                    unsafe_allow_html=True,
                )

            c_inp, c_add = st.columns([4, 1])
            new_num = c_inp.text_input(
                "Número",
                placeholder="5549999999999",
                label_visibility="collapsed",
                key=f"new_num_{account_id}",
            )
            if c_add.button("＋", key=f"add_{account_id}", use_container_width=True, help="Adicionar número"):
                cleaned = new_num.strip().replace("+", "").replace(" ", "").replace("-", "")
                if cleaned.isdigit() and len(cleaned) >= 10:
                    if cleaned not in st.session_state[nums_key]:
                        st.session_state[nums_key].append(cleaned)
                        if client_url and evo.get("base_url"):
                            send_message(
                                evo["base_url"], evo["instance"], evo["apikey"], cleaned,
                                f"👋 Olá! Seu painel de acompanhamento de anúncios está disponível.\n\n"
                                f"📊 Acesse aqui: {client_url}\n\n"
                                f"O link é exclusivo para a sua conta. Guarde-o com segurança.",
                            )
                        st.rerun()
                    else:
                        st.warning("Número já cadastrado.")
                else:
                    st.error("Inválido. Use dígitos no formato internacional, ex: `5549999999999`")

            st.markdown("")
            with st.expander("Adicionar grupo do WhatsApp"):
                grp_key = f"_grps_{account_id}"
                if grp_key not in st.session_state:
                    st.session_state[grp_key] = None

                if not evo.get("base_url"):
                    st.warning("Configure a Evolution API em `config_alertas.json` primeiro.")
                else:
                    if st.button("Buscar grupos", key=f"fetch_grps_{account_id}"):
                        with st.spinner("Buscando grupos..."):
                            st.session_state[grp_key] = list_groups(
                                evo["base_url"], evo["instance"], evo["apikey"]
                            )

                    groups = st.session_state[grp_key]
                    if groups is None:
                        st.caption("Clique em 'Buscar grupos' para listar os grupos da instância.")
                    elif len(groups) == 0:
                        st.warning("Nenhum grupo encontrado. Verifique se a instância está conectada.")
                    else:
                        opts = {f"{g['subject']}  ({g['id']})": g["id"] for g in groups}
                        sel_grp = st.selectbox(
                            "Grupo", list(opts.keys()),
                            key=f"sel_grp_{account_id}",
                        )
                        if st.button("Adicionar grupo", key=f"add_grp_{account_id}", use_container_width=True):
                            jid = opts[sel_grp]
                            if jid not in st.session_state[nums_key]:
                                st.session_state[nums_key].append(jid)
                                st.rerun()
                            else:
                                st.warning("Grupo já adicionado.")

        # ── Linha divisória + botões de ação ─────────────────────────────────────
        st.markdown(
            '<div style="height:1px;background:rgba(56,189,248,0.08);margin:1rem 0 0.8rem;"></div>',
            unsafe_allow_html=True,
        )
        col_save, col_test, _spc = st.columns([1, 1, 4])

        if col_save.button("Salvar", key=f"save_{account_id}", type="primary", use_container_width=True):
            cfg["contas"][idx]["monitor_leads"]         = bool(st.session_state.get(f"tog_leads_{account_id}", False))
            cfg["contas"][idx]["monitor_conversations"] = bool(st.session_state.get(f"tog_conv_{account_id}", False))
            nums_to_save = list(st.session_state[nums_key])
            cfg["contas"][idx]["whatsapps"] = nums_to_save
            cfg["contas"][idx]["whatsapp"]  = nums_to_save[0] if nums_to_save else ""
            _save_config(cfg)
            _load_log.clear()
            st.success(f"Configurações de **{label}** salvas.")
            st.rerun()

        if col_test.button("Testar envio", key=f"test_{account_id}", use_container_width=True):
            if not evo.get("base_url"):
                st.error("Evolution API não configurada em `config_alertas.json`.")
            elif not st.session_state[nums_key]:
                st.error("Nenhum destinatário cadastrado.")
            else:
                tipos = []
                if st.session_state.get(f"tog_leads_{account_id}"):  tipos.append("Leads")
                if st.session_state.get(f"tog_conv_{account_id}"):   tipos.append("Conversas")
                tipo_txt = " · ".join(tipos) if tipos else "Nenhum ativo"
                test_msg = (
                    f"✅ *Teste — Meta Ads Dashboard*\n"
                    f"Conta: _{label}_\n"
                    f"Monitoramento: {tipo_txt}\n"
                    f"⏰ {now_br().strftime('%d/%m/%Y %H:%M')}"
                )
                failed, success = [], 0
                for num in st.session_state[nums_key]:
                    ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], num, test_msg)
                    if ok: success += 1
                    else:  failed.append(_fmt_number(num))
                if success:
                    st.success(f"Mensagem enviada para {success} destinatário(s).")
                if failed:
                    st.error(f"Falha: {', '.join(failed)}")

        # ── Acesso do cliente ────────────────────────────────────────────────────
        st.markdown(
            '<div style="height:1px;background:rgba(56,189,248,0.08);margin:0.8rem 0;"></div>'
            + _label("Acesso do cliente"),
            unsafe_allow_html=True,
        )

        client_token = account.get("client_token", "")
        client_url   = f"{public_url}/Cliente?token={client_token}" if (public_url and client_token) else None

        def _send_panel_link(url: str, nums: list):
            if not evo.get("base_url") or not nums:
                return
            msg = (
                f"👋 Olá! Seu painel de acompanhamento de anúncios está disponível.\n\n"
                f"📊 Acesse aqui: {url}\n\n"
                f"O link é exclusivo para a sua conta. Guarde-o com segurança."
            )
            for n in nums:
                send_message(evo["base_url"], evo["instance"], evo["apikey"], n, msg)

        if client_token:
            if not public_url:
                st.warning("Configure `public_url` no `config_alertas.json` para gerar o link correto.")
            else:
                st.markdown(
                    f'<div style="background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.14);'
                    f'border-radius:10px;padding:0.6rem 1rem;margin-bottom:0.75rem;">'
                    f'<div style="color:#1A3A5C;font-size:0.67rem;font-weight:700;letter-spacing:0.08em;'
                    f'text-transform:uppercase;margin-bottom:0.3rem;">Link ativo</div>'
                    f'<code style="color:#7DD3FC;font-size:0.79rem;word-break:break-all;">{client_url}</code>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            col_regen, col_revoke, col_send, _spc2 = st.columns([1, 1, 1, 3])
            if col_regen.button("Regenerar", key=f"regen_{account_id}", use_container_width=True,
                                help="Gera um novo token — o link anterior deixa de funcionar"):
                cfg["contas"][idx]["client_token"] = secrets.token_urlsafe(8)
                _save_config(cfg)
                st.success("Novo link gerado.")
                st.rerun()
            if col_revoke.button("Revogar", key=f"revoke_{account_id}", use_container_width=True,
                                 help="Remove o acesso — o link atual deixa de funcionar"):
                cfg["contas"][idx]["client_token"] = ""
                _save_config(cfg)
                st.success("Acesso revogado.")
                st.rerun()
            if client_url and col_send.button("Enviar link", key=f"send_link_{account_id}",
                                              use_container_width=True,
                                              help="Envia o link do painel para os destinatários cadastrados"):
                send_nums = st.session_state[nums_key]
                if not send_nums:
                    st.warning("Nenhum destinatário cadastrado.")
                elif not evo.get("base_url"):
                    st.error("Evolution API não configurada.")
                else:
                    _send_panel_link(client_url, send_nums)
                    st.success(f"Link enviado para {len(send_nums)} destinatário(s).")
        else:
            st.markdown(
                '<span style="color:#1E3A5A;font-size:0.82rem;">Nenhum link ativo para esta conta.</span>',
                unsafe_allow_html=True,
            )
            col_gen, _spc3 = st.columns([2, 4])
            if col_gen.button("Gerar link de acesso", key=f"gen_{account_id}", use_container_width=True):
                new_token = secrets.token_urlsafe(8)
                cfg["contas"][idx]["client_token"] = new_token
                _save_config(cfg)
                new_url = f"{public_url}/Cliente?token={new_token}" if public_url else None
                if new_url:
                    gen_nums = st.session_state[nums_key]
                    if gen_nums and evo.get("base_url"):
                        _send_panel_link(new_url, gen_nums)
                        st.success("Link gerado e enviado automaticamente.")
                    else:
                        st.success("Link gerado. Copie e compartilhe com o cliente.")
                else:
                    st.success("Link gerado.")
                st.rerun()

# ── Rodapé ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="color:#1E3A5A;font-size:0.75rem;margin:0.5rem 0 1.6rem;">'
    'Runner <code style="background:rgba(56,189,248,0.08);padding:0.1rem 0.35rem;border-radius:4px;'
    'color:#7C5BA8;font-size:0.70rem;">alertas_runner.py</code> '
    '· a cada 15 min · horário ativo 06:00–23:00</div>',
    unsafe_allow_html=True,
)

# ── Histórico de performance ─────────────────────────────────────────────────────
history_all = log.get("history", {})
if history_all:
    st.markdown(
        section_header("Histórico de performance", "evolução diária registrada pelo runner"),
        unsafe_allow_html=True,
    )
    acct_options = {a.get("label", a["account_id"]): a["account_id"] for a in contas}
    hist_label   = st.selectbox("Conta", list(acct_options.keys()), key="hist_acct")
    sel_id       = acct_options[hist_label]
    hist         = history_all.get(sel_id, {})

    if hist:
        df_h = pd.DataFrame([{"data": k, **v} for k, v in sorted(hist.items())])
        df_h["data"] = pd.to_datetime(df_h["data"])

        metric = st.radio(
            "Métrica",
            ["spend", "leads", "conversations", "cpl"],
            format_func=lambda x: {
                "spend": "Investimento (R$)", "leads": "Leads",
                "conversations": "Conversas",  "cpl": "CPL (R$)",
            }[x],
            horizontal=True, key="hist_metric",
        )

        df_plot = df_h.dropna(subset=[metric])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_plot["data"], y=df_plot[metric],
            mode="lines+markers",
            line=dict(color="#38BDF8", width=2),
            marker=dict(color="#F59E0B", size=6),
            fill="tozeroy",
            fillcolor="rgba(56,189,248,0.08)",
            hovertemplate="%{x|%d/%m}<br>%{y:.2f}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=220,
            xaxis=dict(showgrid=False, color="#4A7A9B"),
            yaxis=dict(gridcolor="#0A1428", color="#4A7A9B"),
            font=dict(color="#93C5FD"),
            transition=dict(duration=420, easing="cubic-in-out"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(
            f"{len(df_h)} dias registrados · último: {df_h['data'].max().strftime('%d/%m/%Y')}"
        )
    else:
        st.caption("Nenhum dado histórico para esta conta ainda. O runner irá registrar a partir do próximo ciclo.")
