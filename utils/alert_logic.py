"""
Regras de alerta e builder do relatório diário.
"""
from datetime import datetime


def check_alerts(insights: list, campaigns_budget: list, thresholds: dict) -> list:
    """
    Verifica condições de alerta para uma conta.
    Retorna lista de dicts com 'key' (sem data — persiste entre dias) e 'msg'.
    A deduplicação e controle de novo/persistente fica em alertas_runner.py.
    """
    budget_warning_pct = thresholds.get("budget_warning_pct", 70) / 100
    ctr_min  = thresholds.get("ctr_min", 0.5)
    cpm_max  = thresholds.get("cpm_max", 50.0)
    cpl_max  = thresholds.get("cpl_max")

    budget_map: dict[str, float] = {}
    for c in campaigns_budget:
        daily    = int(c.get("daily_budget") or 0)
        lifetime = int(c.get("lifetime_budget") or 0)
        cents = daily if daily > 0 else lifetime
        if cents > 0:
            budget_map[c["id"]] = cents / 100.0

    alerts = []

    for row in insights:
        cid   = row["campaign_id"]
        name  = row["campaign_name"]
        spend = row["spend"]
        imp   = row["impressions"]
        ctr   = row["ctr"]
        cpm   = row["cpm"]
        leads = row["leads"]
        conv  = row["conversations"]
        has_conversion = leads > 0 or conv > 0

        budget = budget_map.get(cid, 0)
        if budget > 0:
            pct = spend / budget
            if pct >= 1.0:
                alerts.append({
                    "key": f"{cid}_budget_100",
                    "msg": (
                        f"🔴 *Orçamento esgotado!*\n"
                        f"Campanha: {name}\n"
                        f"Gasto: R$ {spend:.2f} / R$ {budget:.2f} (100%)\n"
                        f"Conversas: {int(conv)} | Leads: {int(leads)}"
                    ),
                })
            elif pct >= budget_warning_pct and not has_conversion:
                alerts.append({
                    "key": f"{cid}_budget_warn",
                    "msg": (
                        f"⚠️ *{int(pct * 100)}% do orçamento sem conversão*\n"
                        f"Campanha: {name}\n"
                        f"Gasto: R$ {spend:.2f} / R$ {budget:.2f}\n"
                        f"Conversas: {int(conv)} | Leads: {int(leads)}"
                    ),
                })

        if imp >= 500:
            if ctr < ctr_min:
                alerts.append({
                    "key": f"{cid}_ctr",
                    "msg": (
                        f"📉 *CTR abaixo do mínimo*\n"
                        f"Campanha: {name}\n"
                        f"CTR: {ctr:.2f}% (mínimo: {ctr_min}%)\n"
                        f"Impressões: {imp:,} | Investimento: R$ {spend:.2f}"
                    ),
                })
            if cpm > cpm_max:
                alerts.append({
                    "key": f"{cid}_cpm",
                    "msg": (
                        f"💸 *CPM acima do limite*\n"
                        f"Campanha: {name}\n"
                        f"CPM: R$ {cpm:.2f} (máximo: R$ {cpm_max:.2f})\n"
                        f"Impressões: {imp:,} | Investimento: R$ {spend:.2f}"
                    ),
                })

        if cpl_max and leads > 0:
            cpl = spend / leads
            if cpl > cpl_max:
                alerts.append({
                    "key": f"{cid}_cpl",
                    "msg": (
                        f"💸 *CPL acima do limite*\n"
                        f"Campanha: {name}\n"
                        f"CPL: R$ {cpl:.2f} (máximo: R$ {cpl_max:.2f})\n"
                        f"Leads: {int(leads)} | Investimento: R$ {spend:.2f}"
                    ),
                })

    return alerts


def build_daily_report(label: str, insights: list, date_str: str, persistent_alerts: list) -> str:
    """
    Monta o relatório diário para envio via WhatsApp.
    persistent_alerts: alertas ainda ativos (já notificados antes, sem alteração).
    Cada item: {"msg": str, "ts_first": str, ...}
    """
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")

    if not insights:
        return (
            f"📊 *Relatório Diário — {label}*\n"
            f"Data: {date_fmt}\n\n"
            f"Nenhum dado disponível para este período."
        )

    total_spend = sum(r["spend"] for r in insights)
    total_imp   = sum(r["impressions"] for r in insights)
    total_clicks = sum(r["clicks"] for r in insights)
    total_leads  = sum(r["leads"] for r in insights)
    total_conv   = sum(r["conversations"] for r in insights)
    avg_ctr = total_clicks / total_imp * 100 if total_imp > 0 else 0
    avg_cpm = total_spend / total_imp * 1000 if total_imp > 0 else 0

    top = max(insights, key=lambda r: r["spend"])

    lines = [
        f"📊 *Relatório Diário — {label}*",
        f"Data: {date_fmt}",
        "",
        f"💰 Investimento: R$ {total_spend:,.2f}",
        f"👁️ Impressões: {total_imp:,}",
        f"📊 CTR médio: {avg_ctr:.2f}%",
        f"💸 CPM médio: R$ {avg_cpm:.2f}",
    ]

    if total_conv > 0:
        cpc_conv = total_spend / total_conv
        lines.append(f"💬 Conversas: {int(total_conv)} | Custo/conversa: R$ {cpc_conv:.2f}")
    if total_leads > 0:
        cpl = total_spend / total_leads
        lines.append(f"🎯 Leads: {int(total_leads)} | CPL: R$ {cpl:.2f}")
    if total_conv == 0 and total_leads == 0:
        lines.append("❌ Sem conversas ou leads no período")

    # Top campanha
    top_conv  = int(top["conversations"])
    top_leads = int(top["leads"])
    top_extra = ""
    if top_conv > 0:
        top_extra = f" | 💬 {top_conv} conversas"
    elif top_leads > 0:
        top_extra = f" | 🎯 {top_leads} leads"
    lines += [
        "",
        f"🏆 Top campanha: _{top['campaign_name']}_",
        f"   R$ {top['spend']:,.2f}{top_extra}",
    ]

    # Alertas persistentes (sem alteração desde a última notificação)
    lines.append("")
    if persistent_alerts:
        lines.append(f"⏳ *Alertas persistentes ({len(persistent_alerts)} sem alteração):*")
        for a in persistent_alerts[:5]:
            first_line = a["msg"].split("\n")[0]
            since = ""
            if "ts_first" in a:
                try:
                    dt = datetime.fromisoformat(a["ts_first"])
                    since = f" — desde {dt.strftime('%d/%m %H:%M')}"
                except Exception:
                    pass
            lines.append(f"  • {first_line}{since}")
        if len(persistent_alerts) > 5:
            lines.append(f"  • ...e mais {len(persistent_alerts) - 5}")
    else:
        lines.append("✅ Nenhum alerta ativo")

    return "\n".join(lines)


def check_lead_increment(
    current: list,
    snapshot: dict,
    monitor_leads: bool,
    monitor_conversations: bool,
) -> list:
    """
    Compara leads/conversas atuais com o snapshot anterior.
    Retorna alertas apenas para incrementos reais.
    snapshot vazio ({}) = primeira execução do dia → estabelece baseline sem alertar.
    """
    if not (monitor_leads or monitor_conversations):
        return []

    leads_snap = snapshot.get("leads")       # None = primeira execução (sem alert)
    conv_snap  = snapshot.get("conversations")
    alerts     = []
    now_fmt    = datetime.now().strftime("%H:%M")

    for row in current:
        cid  = row["campaign_id"]
        name = row["campaign_name"]

        if monitor_leads and leads_snap is not None:
            old   = leads_snap.get(cid, 0)
            cur   = int(row["leads"])
            delta = cur - old
            if delta > 0:
                plural = "leads" if delta > 1 else "lead"
                alerts.append({
                    "msg": (
                        f"🎯 *{delta} novo{'s' if delta > 1 else ''} {plural}!*\n"
                        f"Campanha: _{name}_\n"
                        f"Total hoje: {cur} {plural}\n"
                        f"⏰ {now_fmt}"
                    )
                })

        if monitor_conversations and conv_snap is not None:
            old   = conv_snap.get(cid, 0)
            cur   = int(row["conversations"])
            delta = cur - old
            if delta > 0:
                plural = "conversas" if delta > 1 else "conversa"
                alerts.append({
                    "msg": (
                        f"💬 *{delta} nova{'s' if delta > 1 else ''} {plural} iniciada{'s' if delta > 1 else ''}!*\n"
                        f"Campanha: _{name}_\n"
                        f"Total hoje: {cur} {plural}\n"
                        f"⏰ {now_fmt}"
                    )
                })

    return alerts


def build_snapshot(current: list) -> dict:
    """Gera snapshot dos contadores atuais para comparação no próximo ciclo."""
    return {
        "date":          datetime.now().strftime("%Y-%m-%d"),
        "ts":            datetime.now().isoformat(),
        "leads":         {r["campaign_id"]: int(r["leads"])         for r in current},
        "conversations": {r["campaign_id"]: int(r["conversations"]) for r in current},
    }


def build_persistent_summary(label: str, persistent_alerts: list) -> str:
    """
    Resumo compacto dos alertas ainda ativos, enviado a cada ciclo.
    persistent_alerts: lista de dicts do log["active"] desta conta.
    """
    now_fmt = datetime.now().strftime("%H:%M")
    lines = [
        f"⏳ *{len(persistent_alerts)} alerta(s) não resolvido(s) — {label}*",
        f"Verificação: {now_fmt}",
        "",
    ]
    for a in persistent_alerts:
        first_line = a["msg"].split("\n")[0]
        since = ""
        if "ts_first" in a:
            try:
                dt = datetime.fromisoformat(a["ts_first"])
                since = f" (desde {dt.strftime('%d/%m %H:%M')})"
            except Exception:
                pass
        lines.append(f"• {first_line}{since}")
    return "\n".join(lines)
