"""
Regras de alerta e builder do relatório diário.
"""
from datetime import datetime


def check_alerts(insights: list, campaigns_budget: list, thresholds: dict, date_str: str) -> list:
    """
    Verifica condições de alerta para uma conta.
    Retorna lista de dicts com 'key' (deduplicação) e 'msg' (texto WhatsApp).
    """
    budget_warning_pct = thresholds.get("budget_warning_pct", 70) / 100
    ctr_min  = thresholds.get("ctr_min", 0.5)
    cpm_max  = thresholds.get("cpm_max", 50.0)
    cpl_max  = thresholds.get("cpl_max")   # None = sem limite

    # Mapa campaign_id -> orçamento diário em R$ (0 se não tiver)
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

        # ── Alertas de orçamento ──────────────────────────────────────────────
        budget = budget_map.get(cid, 0)
        if budget > 0:
            pct = spend / budget
            if pct >= 1.0:
                alerts.append({
                    "key": f"{cid}_budget_100_{date_str}",
                    "msg": (
                        f"🔴 *Orçamento esgotado!*\n"
                        f"Campanha: {name}\n"
                        f"Gasto: R$ {spend:.2f} / R$ {budget:.2f} (100%)\n"
                        f"Conversas: {int(conv)} | Leads: {int(leads)}"
                    ),
                })
            elif pct >= budget_warning_pct and not has_conversion:
                alerts.append({
                    "key": f"{cid}_budget_warn_{date_str}",
                    "msg": (
                        f"⚠️ *{int(pct * 100)}% do orçamento sem conversão*\n"
                        f"Campanha: {name}\n"
                        f"Gasto: R$ {spend:.2f} / R$ {budget:.2f}\n"
                        f"Conversas: {int(conv)} | Leads: {int(leads)}"
                    ),
                })

        # ── Alertas de métricas (mín. 500 impressões) ────────────────────────
        if imp >= 500:
            if ctr < ctr_min:
                alerts.append({
                    "key": f"{cid}_ctr_{date_str}",
                    "msg": (
                        f"📉 *CTR abaixo do mínimo*\n"
                        f"Campanha: {name}\n"
                        f"CTR: {ctr:.2f}% (mínimo: {ctr_min}%)\n"
                        f"Impressões: {imp:,} | Investimento: R$ {spend:.2f}"
                    ),
                })
            if cpm > cpm_max:
                alerts.append({
                    "key": f"{cid}_cpm_{date_str}",
                    "msg": (
                        f"💸 *CPM acima do limite*\n"
                        f"Campanha: {name}\n"
                        f"CPM: R$ {cpm:.2f} (máximo: R$ {cpm_max:.2f})\n"
                        f"Impressões: {imp:,} | Investimento: R$ {spend:.2f}"
                    ),
                })

        # ── Alerta de CPL ─────────────────────────────────────────────────────
        if cpl_max and leads > 0:
            cpl = spend / leads
            if cpl > cpl_max:
                alerts.append({
                    "key": f"{cid}_cpl_{date_str}",
                    "msg": (
                        f"💸 *CPL acima do limite*\n"
                        f"Campanha: {name}\n"
                        f"CPL: R$ {cpl:.2f} (máximo: R$ {cpl_max:.2f})\n"
                        f"Leads: {int(leads)} | Investimento: R$ {spend:.2f}"
                    ),
                })

    return alerts


def build_daily_report(label: str, insights: list, date_str: str, alerts_yesterday: list) -> str:
    """
    Monta o relatório diário para envio via WhatsApp.
    alerts_yesterday: lista de dicts com chave 'msg' (alertas do dia anterior).
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

    # Resumo de alertas do dia anterior
    lines.append("")
    if alerts_yesterday:
        lines.append(f"⚠️ Alertas disparados: {len(alerts_yesterday)}")
        for a in alerts_yesterday[:3]:
            first_line = a["msg"].split("\n")[0]
            lines.append(f"  • {first_line}")
        if len(alerts_yesterday) > 3:
            lines.append(f"  • ...e mais {len(alerts_yesterday) - 3}")
    else:
        lines.append("✅ Nenhum alerta disparado ontem")

    return "\n".join(lines)
