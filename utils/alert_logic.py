"""
Regras de alerta e builder do relatório diário.
"""
import calendar
from datetime import datetime, timedelta
from utils.tz import now_br


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
    now_fmt    = now_br().strftime("%H:%M")

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


def check_budget_pace(history: dict, today_str: str, campaigns_budget: list) -> list:
    """
    Verifica se o ritmo de gasto do mês atual projeta estouro do orçamento.
    Só alerta se a projeção superar 15% acima do orçamento total estimado.
    Requer ao menos 3 dias de histórico no mês para ser relevante.
    """
    try:
        today      = datetime.strptime(today_str, "%Y-%m-%d")
        month_start = today.replace(day=1).strftime("%Y-%m-%d")
        days_elapsed = today.day
        days_in_month = calendar.monthrange(today.year, today.month)[1]

        month_spend = sum(
            v["spend"] for k, v in history.items()
            if k >= month_start
        )
        if days_elapsed < 3 or month_spend == 0:
            return []

        daily_avg      = month_spend / days_elapsed
        projected_total = daily_avg * days_in_month

        total_budget = sum(
            (int(c.get("daily_budget") or 0) / 100.0) * days_in_month
            for c in campaigns_budget
            if int(c.get("daily_budget") or 0) > 0
        )
        if total_budget <= 0 or projected_total <= total_budget * 1.15:
            return []

        esgota_dia = int(total_budget / daily_avg) if daily_avg > 0 else days_in_month
        return [{
            "key": f"budget_pace_{today.strftime('%Y-%m')}",
            "msg": (
                f"📈 *Ritmo de gasto acima do orçamento*\n"
                f"Média diária: R$ {daily_avg:.2f}\n"
                f"Projeção mensal: R$ {projected_total:.2f}\n"
                f"Orçamento estimado: R$ {total_budget:.2f}\n"
                f"⚠️ No ritmo atual, orçamento esgota ~dia {esgota_dia}"
            ),
        }]
    except Exception:
        return []


# account_status da Graph API que indicam risco de pagamento/conta travada:
# 2=Disabled, 3=Unsettled, 9=In Grace Period, 100=Pending Closure
_RISCO_PAGAMENTO = {2, 3, 9, 100}


def check_saldo(account_id: str, label: str, info: dict, account_cfg: dict) -> list:
    """
    Verifica saldo baixo / limite de gasto próximo do fim + status de pagamento
    da conta.

    'disponível' = spend_cap - amount_spent, sempre que a conta tem um
    spend_cap configurado (>0) — é assim que o "pré-pago" funciona na prática
    aqui (depósito PIX vira um AUMENTO do spend_cap na conta, não um saldo
    separado). Contas sem spend_cap configurado (cobrança automática por
    cartão) não têm um "saldo" comparável vindo desses campos — 'balance' da
    Graph API ali é só o valor da fatura em aberto, não crédito disponível, e
    NÃO deve ser usado como "saldo disponível" (confirmado contra conta real:
    dava um número ~5x menor que o saldo de verdade mostrado no Ads Manager).
    Pra essas, só o status de pagamento é monitorado.

    account_cfg é o dict da conta em config_alertas.json (tem
    'thresholds.saldo_minimo', opcional — sem ele, a checagem de saldo fica
    desligada pra essa conta, só o status de pagamento continua ativo).
    """
    alerts = []
    status = info.get("account_status")
    if status in _RISCO_PAGAMENTO:
        alerts.append({
            "key": f"{account_id}_status_pagamento",
            "msg": (
                f"🚨 *Problema de pagamento*\n"
                f"Conta: {label}\n"
                f"Status: {status} — verifique o método de pagamento no Ads Manager."
            ),
        })

    saldo_minimo = (account_cfg.get("thresholds") or {}).get("saldo_minimo")
    if saldo_minimo is None:
        return alerts  # checagem de saldo desligada pra essa conta (não configurada)

    moeda = info.get("currency", "BRL")
    # balance/spend_cap/amount_spent vêm como STRING na Graph API (confirmado
    # contra conta real) — sem o int(), a divisão abaixo levanta TypeError e o
    # alerta nunca dispara (silenciosamente engolido pelo try/except do runner).
    cap = int(info.get("spend_cap") or 0)
    if cap <= 0:
        return alerts  # sem spend_cap configurado: nada comparável a "saldo" pra essa conta
    disponivel = cap / 100.0 - int(info.get("amount_spent") or 0) / 100.0

    if disponivel < saldo_minimo:
        alerts.append({
            "key": f"{account_id}_saldo_baixo",
            "msg": (
                f"💰 *Saldo baixo*\n"
                f"Conta: {label}\n"
                f"Disponível: {moeda} {disponivel:.2f} (mínimo configurado: {moeda} {saldo_minimo:.2f})"
            ),
        })
    return alerts


def build_snapshot(current: list) -> dict:
    """Gera snapshot dos contadores atuais para comparação no próximo ciclo."""
    return {
        "date":          now_br().strftime("%Y-%m-%d"),
        "ts":            now_br().isoformat(),
        "leads":         {r["campaign_id"]: int(r["leads"])         for r in current},
        "conversations": {r["campaign_id"]: int(r["conversations"]) for r in current},
    }


def build_persistent_summary(label: str, persistent_alerts: list) -> str:
    """
    Resumo compacto dos alertas ainda ativos, enviado a cada ciclo.
    persistent_alerts: lista de dicts do log["active"] desta conta.
    """
    now_fmt = now_br().strftime("%H:%M")
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
