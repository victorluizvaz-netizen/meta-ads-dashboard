import calendar
import uuid
from datetime import datetime, timedelta, date

import streamlit as st

from utils.client_guard import redirect_if_client
from utils.config_loader import load_config, save_config
from utils.styles import css, section_header

st.set_page_config(page_title="Agendamentos | Meta Ads", page_icon="🗓️", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

redirect_if_client()

# ── Helpers ───────────────────────────────────────────────────────────────────

FREQ_LABELS = {
    "once":    "Uma vez",
    "daily":   "Diário",
    "weekly":  "Semanal",
    "monthly": "Mensal",
}

PERIOD_OPTIONS = {
    "Últimos 7 dias":   ("last_n_days", 7),
    "Últimos 15 dias":  ("last_n_days", 15),
    "Últimos 30 dias":  ("last_n_days", 30),
    "Mês atual":        ("current_month", 0),
    "Mês anterior":     ("previous_month", 0),
}

DOW_LABELS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

ALL_SECTIONS = [
    "Alertas e Sugestões", "Visão Geral", "Awareness",
    "Tráfego", "Leads", "Conversões", "Conjuntos de Anúncios", "Criativos",
]

FORMAT_LABELS = {"pdf": "PDF", "html": "HTML", "both": "PDF + HTML"}


def _compute_next_run(freq: str, run_time, run_date=None,
                      day_of_week: int = 0, day_of_month: int = 1) -> str:
    now = datetime.now()
    h, m = run_time.hour, run_time.minute

    if freq == "once":
        dt = datetime.combine(run_date, datetime.min.time()).replace(hour=h, minute=m)
        return dt.isoformat()

    if freq == "daily":
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.isoformat()

    if freq == "weekly":
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        days_fwd  = (day_of_week - candidate.weekday()) % 7
        if days_fwd == 0 and candidate <= now:
            days_fwd = 7
        return (candidate + timedelta(days=days_fwd)).isoformat()

    # monthly
    try:
        candidate = now.replace(day=day_of_month, hour=h, minute=m, second=0, microsecond=0)
    except ValueError:
        max_day   = calendar.monthrange(now.year, now.month)[1]
        candidate = now.replace(day=min(day_of_month, max_day), hour=h, minute=m, second=0, microsecond=0)
    if candidate <= now:
        next_month = now.month % 12 + 1
        next_year  = now.year + (1 if now.month == 12 else 0)
        max_day    = calendar.monthrange(next_year, next_month)[1]
        candidate  = candidate.replace(year=next_year, month=next_month, day=min(day_of_month, max_day))
    return candidate.isoformat()


def _freq_badge(freq: str) -> str:
    colors = {"once": "#6C63FF", "daily": "#2ECC71", "weekly": "#F39C12", "monthly": "#E74C3C"}
    return (
        f"<span style='background:{colors.get(freq,'#888')};color:white;"
        f"border-radius:4px;padding:2px 8px;font-size:0.75rem;font-weight:600'>"
        f"{FREQ_LABELS.get(freq, freq)}</span>"
    )


def _period_label(sched: dict) -> str:
    mode = sched.get("period_mode", "last_n_days")
    days = sched.get("period_days", 30)
    if mode == "current_month":
        return "Mês atual"
    if mode == "previous_month":
        return "Mês anterior"
    return f"Últimos {days} dias"


# ── Carrega config ─────────────────────────────────────────────────────────────

cfg      = load_config()
contas   = cfg.get("contas", [])
evo      = cfg.get("evolution_api", {})

if not contas:
    st.warning("Nenhuma conta configurada. Adicione contas em config_alertas.json.")
    st.stop()

# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🗓️ Agendamentos de Relatório")
st.caption("Programe envios automáticos de relatórios via WhatsApp com recorrência ou data única.")
st.divider()

col_form, col_list = st.columns([1, 1.4], gap="large")

# ═══════════════════════ FORMULÁRIO DE NOVO AGENDAMENTO ══════════════════════

with col_form:
    st.markdown(section_header("Novo agendamento"), unsafe_allow_html=True)

    # Conta
    conta_labels = {c["account_id"]: c.get("label", c["account_id"]) for c in contas}
    conta_sel    = st.selectbox(
        "Conta", options=list(conta_labels.keys()),
        format_func=lambda x: conta_labels[x],
        key="sched_account",
    )
    conta_cfg = next((c for c in contas if c["account_id"] == conta_sel), {})

    client_name = st.text_input(
        "Nome do cliente (cabeçalho do relatório)",
        value=conta_cfg.get("label", ""),
        key="sched_client_name",
    )

    st.markdown(section_header("Frequência"), unsafe_allow_html=True)

    freq = st.radio(
        "Recorrência",
        options=list(FREQ_LABELS.keys()),
        format_func=lambda x: FREQ_LABELS[x],
        horizontal=True,
        key="sched_freq",
    )

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        run_time = st.time_input("Horário", value=datetime.strptime("08:00", "%H:%M").time(), key="sched_time")
    with col_t2:
        if freq == "once":
            run_date = st.date_input("Data", value=date.today() + timedelta(days=1), key="sched_date")
            day_of_week  = 0
            day_of_month = 1
        elif freq == "weekly":
            dow_sel      = st.selectbox("Dia da semana", options=list(range(7)),
                                        format_func=lambda x: DOW_LABELS[x], key="sched_dow")
            day_of_week  = dow_sel
            day_of_month = 1
            run_date     = None
        elif freq == "monthly":
            day_of_month = st.number_input("Dia do mês", min_value=1, max_value=28, value=1, key="sched_dom")
            day_of_week  = 0
            run_date     = None
        else:  # daily
            st.caption("Todo dia no horário acima")
            day_of_week  = 0
            day_of_month = 1
            run_date     = None

    st.markdown(section_header("Período do relatório"), unsafe_allow_html=True)

    period_sel  = st.selectbox("Período", options=list(PERIOD_OPTIONS.keys()), key="sched_period")
    period_mode, period_days = PERIOD_OPTIONS[period_sel]

    st.markdown(section_header("Destinatários"), unsafe_allow_html=True)

    registered_nums = conta_cfg.get("whatsapps") or (
        [conta_cfg["whatsapp"]] if conta_cfg.get("whatsapp") else []
    )
    registered_opts = [f"+{n}" for n in registered_nums]

    selected_registered = st.multiselect(
        "Números cadastrados",
        options=registered_opts,
        default=registered_opts,
        key="sched_nums_reg",
    )
    custom_nums_raw = st.text_input(
        "Outros números (separados por vírgula)",
        placeholder="5549999999999, 5549888888888",
        key="sched_nums_custom",
    )
    custom_nums = [
        n.strip().lstrip("+").replace(" ", "").replace("-", "")
        for n in custom_nums_raw.split(",") if n.strip()
    ]
    all_recipients = [n.lstrip("+") for n in selected_registered] + custom_nums

    st.markdown(section_header("Formato e seções"), unsafe_allow_html=True)

    fmt = st.radio(
        "Formato do arquivo",
        options=list(FORMAT_LABELS.keys()),
        format_func=lambda x: FORMAT_LABELS[x],
        horizontal=True,
        key="sched_format",
        index=0,
    )

    sections = st.multiselect(
        "Seções",
        options=ALL_SECTIONS,
        default=ALL_SECTIONS,
        key="sched_sections",
    )

    notes = st.text_area(
        "Observações (opcional)",
        placeholder="Ex: Período de lançamento de nova campanha.",
        height=70,
        key="sched_notes",
    )

    st.divider()

    if st.button("➕ Criar agendamento", type="primary", use_container_width=True):
        erros = []
        if not client_name.strip():
            erros.append("Preencha o nome do cliente.")
        if not all_recipients:
            erros.append("Adicione ao menos um destinatário.")
        if not sections:
            erros.append("Selecione ao menos uma seção.")
        if freq == "once" and run_date and run_date < date.today():
            erros.append("A data deve ser hoje ou no futuro.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            next_run = _compute_next_run(
                freq, run_time, run_date,
                day_of_week=day_of_week, day_of_month=day_of_month,
            )
            new_sched = {
                "id":           str(uuid.uuid4()),
                "account_id":   conta_sel,
                "client_name":  client_name.strip(),
                "frequency":    freq,
                "day_of_week":  day_of_week,
                "day_of_month": day_of_month,
                "run_date":     run_date.isoformat() if run_date else None,
                "run_at":       run_time.strftime("%H:%M"),
                "period_mode":  period_mode,
                "period_days":  period_days,
                "recipients":   all_recipients,
                "format":       fmt,
                "sections":     sections,
                "notes":        notes,
                "enabled":      True,
                "last_run":     None,
                "next_run":     next_run,
            }
            cfg.setdefault("schedules", []).append(new_sched)
            save_config(cfg)
            st.success(f"✅ Agendamento criado! Próximo envio: **{next_run[:16].replace('T', ' ')}**")
            st.rerun()

# ═══════════════════════ LISTA DE AGENDAMENTOS ═══════════════════════════════

with col_list:
    st.markdown(section_header("Agendamentos existentes"), unsafe_allow_html=True)

    schedules = cfg.get("schedules", [])

    if not schedules:
        st.markdown("""
        <div style="background:rgba(19,14,39,0.8);border:1px solid rgba(168,85,247,0.15);border-radius:12px;
        padding:2rem;text-align:center;color:#8B7EAF;">
            <p style="font-size:2rem;margin-bottom:0.5rem;">🗓️</p>
            <p style="font-weight:600;color:#F1ECF8;">Nenhum agendamento ainda</p>
            <p style="font-size:0.85rem;">Crie um agendamento no formulário ao lado.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, sched in enumerate(schedules):
            sched_id     = sched.get("id", str(idx))
            label_conta  = conta_labels.get(sched.get("account_id", ""), sched.get("account_id", "?"))
            client_lbl   = sched.get("client_name") or label_conta
            freq_val     = sched.get("frequency", "once")
            enabled      = sched.get("enabled", True)
            next_run_str = sched.get("next_run")
            last_run_str = sched.get("last_run")
            recipients   = sched.get("recipients", [])
            fmt_val      = sched.get("format", "pdf")

            next_run_fmt = next_run_str[:16].replace("T", " ") if next_run_str else "—"
            last_run_fmt = last_run_str[:16].replace("T", " ") if last_run_str else "nunca"

            status_color = "#2ECC71" if enabled else "#95A5A6"
            status_label = "Ativo" if enabled else "Pausado"

            with st.container(border=True):
                header_col, badge_col = st.columns([3, 1])
                with header_col:
                    st.markdown(
                        f"**{client_lbl}** &nbsp; {_freq_badge(freq_val)} "
                        f"<span style='color:{status_color};font-size:0.8rem'> ● {status_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"Conta: {label_conta} · Formato: {FORMAT_LABELS.get(fmt_val, fmt_val)} · "
                        f"Período: {_period_label(sched)} · "
                        f"{len(recipients)} destinatário(s)"
                    )
                    st.caption(f"Próximo envio: **{next_run_fmt}** · Último: {last_run_fmt}")

                btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1, 1, 2])

                with btn_col1:
                    toggle_label = "⏸ Pausar" if enabled else "▶ Ativar"
                    if st.button(toggle_label, key=f"tog_{sched_id}", use_container_width=True):
                        sched["enabled"] = not enabled
                        cfg["schedules"] = schedules
                        save_config(cfg)
                        st.rerun()

                with btn_col2:
                    if st.button("🗑 Excluir", key=f"del_{sched_id}", use_container_width=True):
                        cfg["schedules"] = [s for s in schedules if s.get("id") != sched_id]
                        save_config(cfg)
                        st.rerun()

                with btn_col3:
                    if st.button("▶ Enviar agora", key=f"now_{sched_id}", use_container_width=True):
                        # Força next_run para agora para que o runner execute na próxima iteração
                        sched["next_run"] = datetime.now().isoformat()
                        cfg["schedules"] = schedules
                        save_config(cfg)
                        st.success("Agendado para o próximo ciclo do runner (≤ 15 min).")
                        st.rerun()
