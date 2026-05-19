#!/usr/bin/env python3
"""
Runner de alertas Meta Ads.
Agendar via Windows Task Scheduler a cada 15 minutos (setup_alertas.ps1).

Frequências:
  - A cada execução (15 min): novos leads e conversas (monitoramento em tempo real)
  - A cada 60 min:            alertas de performance (orçamento, CTR, CPM, CPL)
                              + resumo de persistentes + relatório diário às 08:00

Lógica de notificação (alertas de performance):
  - Alerta NOVO (condição apareceu agora)       → envia mensagem imediatamente
  - Alerta PERSISTENTE (já foi notificado antes) → atualiza timestamp, sem reenvio
  - Alerta RESOLVIDO (condição sumiu)            → remove do registro silenciosamente
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT        = Path(__file__).parent
CONFIG_PATH = ROOT / "config_alertas.json"
LOG_PATH    = ROOT / "alertas_log.json"

# Injeta token Meta como env var ANTES de importar meta_api_bg (lido em import time)
def _bootstrap() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config_alertas.json não encontrado em {ROOT}.\n"
            "Copie config_alertas.example.json, preencha e salve como config_alertas.json."
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    token = cfg.get("meta_access_token", "")
    if token and token != "SEU_TOKEN_META_AQUI":
        os.environ["META_ACCESS_TOKEN"] = token
    return cfg

_CONFIG = _bootstrap()

sys.path.insert(0, str(ROOT))

from utils.meta_api_bg import get_insights_bg, get_campaigns_bg
from utils.whatsapp    import send_message
from utils.alert_logic import (
    check_alerts, build_daily_report, build_persistent_summary,
    check_lead_increment, build_snapshot,
)


def load_log() -> dict:
    """
    Estrutura do log:
      {
        "active":       { "<key>": {"ts_first": ..., "ts_last": ..., "msg": ..., "account_id": ...} },
        "reports_sent": { "<account_id>_<date>": "<iso datetime>" }
      }
    """
    if LOG_PATH.exists():
        with open(LOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Migração de formato antigo (chave plana) para novo formato
        if "active" not in data:
            data = {"active": {}, "reports_sent": {}}
        return data
    return {"active": {}, "reports_sent": {}}


def save_log(log: dict):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


ACTIVE_HOURS         = (6, 23)   # roda das 06:00 às 22:59; fora disso o script sai imediatamente
FULL_CHECK_INTERVAL  = 60        # minutos entre verificações completas de alertas de performance

def is_active_hours() -> bool:
    return ACTIVE_HOURS[0] <= datetime.now().hour < ACTIVE_HOURS[1]

def _should_full_check(log: dict, account_id: str) -> bool:
    """Retorna True se já passaram FULL_CHECK_INTERVAL minutos desde o último check completo."""
    last = log.get("last_full_check", {}).get(account_id)
    if not last:
        return True
    try:
        elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
        return elapsed >= FULL_CHECK_INTERVAL * 60
    except Exception:
        return True

def _mark_full_check(log: dict, account_id: str):
    log.setdefault("last_full_check", {})[account_id] = datetime.now().isoformat()

def _send_all(evo: dict, numbers: list, text: str) -> bool:
    """Envia mensagem para todos os números. Retorna True se ao menos um recebeu."""
    if not numbers:
        return False
    results = []
    for num in numbers:
        ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], num, text)
        results.append(ok)
        if not ok:
            print(f"    ↳ {num}: FALHA")
    return any(results)


def is_report_window(report_time: str) -> bool:
    now = datetime.now()
    h, m = map(int, report_time.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return 0 <= (now - target).total_seconds() < 3600


def main():
    if not is_active_hours():
        print(f"Fora do horário ativo ({ACTIVE_HOURS[0]:02d}:00–{ACTIVE_HOURS[1]:02d}:00). Encerrando.")
        return

    config = _CONFIG
    log    = load_log()

    evo         = config["evolution_api"]
    report_time = config.get("report_time", "08:00")
    today       = datetime.today().strftime("%Y-%m-%d")
    yesterday   = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    now_iso     = datetime.now().isoformat()
    send_report = is_report_window(report_time)

    active       = log["active"]
    reports_sent = log["reports_sent"]

    for account in config.get("contas", []):
        account_id = account["account_id"]
        label      = account.get("label", account_id)
        thresholds = account.get("thresholds", {})

        whatsapps = account.get("whatsapps") or (
            [account["whatsapp"]] if account.get("whatsapp") else []
        )

        run_full = _should_full_check(log, account_id)
        mode_tag = "COMPLETO" if run_full else "LEADS"
        print(f"\n[{label}] Verificando ({mode_tag}) — {datetime.now().strftime('%H:%M')}")

        # ── Sempre: insights de hoje (necessário p/ lead monitoring) ─────────
        try:
            insights_today = get_insights_bg(account_id, today)
        except Exception as e:
            print(f"  ERRO insights: {e}")
            insights_today = []

        # ── Sempre (a cada 15 min): novos leads e conversas ──────────────────
        mon_leads = account.get("monitor_leads", False)
        mon_conv  = account.get("monitor_conversations", False)
        if mon_leads or mon_conv:
            stored_snap = log.get("leads_snapshot", {}).get(account_id, {})
            if stored_snap.get("date") != today:
                stored_snap = {}   # novo dia → reseta baseline sem alertar
            lead_alerts = check_lead_increment(insights_today, stored_snap, mon_leads, mon_conv)
            for la in lead_alerts:
                ok = _send_all(evo, whatsapps, la["msg"])
                print(f"  [LEAD/{'OK' if ok else 'FALHA'}] {la['msg'][:60].replace(chr(10), ' ')}")
            log.setdefault("leads_snapshot", {})[account_id] = build_snapshot(insights_today)

        # ── Snapshot diário de métricas (histórico) ──────────────────────────
        if insights_today:
            total_spend = sum(r.get("spend", 0) for r in insights_today)
            total_leads = sum(r.get("leads", 0) for r in insights_today)
            total_conv  = sum(r.get("conversations", 0) for r in insights_today)
            total_imp   = sum(r.get("impressions", 0) for r in insights_today)
            log.setdefault("history", {}).setdefault(account_id, {})[today] = {
                "spend":         round(total_spend, 2),
                "leads":         int(total_leads),
                "conversations": int(total_conv),
                "impressions":   int(total_imp),
                "cpl":           round(total_spend / total_leads, 2) if total_leads > 0 else None,
            }

        # ── Condicional (a cada 60 min): alertas de performance ──────────────
        if not run_full:
            try:
                last_ts  = log["last_full_check"][account_id]
                mins_ago = int((datetime.now() - datetime.fromisoformat(last_ts)).total_seconds() // 60)
                next_in  = max(0, FULL_CHECK_INTERVAL - mins_ago)
                print(f"  [SKIP] Próximo check completo em ~{next_in} min")
            except Exception:
                print(f"  [SKIP] Aguardando janela de check completo")
            continue

        try:
            campaigns_budget = get_campaigns_bg(account_id)
        except Exception as e:
            print(f"  ERRO campanhas: {e}")
            campaigns_budget = []

        current_alerts      = check_alerts(insights_today, campaigns_budget, thresholds)
        current_keys        = {a["key"] for a in current_alerts}
        account_active_keys = {k for k, v in active.items() if v.get("account_id") == account_id}

        for alert in current_alerts:
            if alert["key"] not in active:
                ok = _send_all(evo, whatsapps, alert["msg"])
                status = "NOVO/OK" if ok else "NOVO/FALHA"
                print(f"  [{status}] {alert['key']}")
                if ok:
                    active[alert["key"]] = {
                        "ts_first":   now_iso,
                        "ts_last":    now_iso,
                        "msg":        alert["msg"],
                        "account_id": account_id,
                        "label":      label,
                    }
            else:
                active[alert["key"]]["ts_last"] = now_iso
                print(f"  [PERSISTENTE] {alert['key']}")

        for key in list(account_active_keys):
            if key not in current_keys:
                del active[key]
                print(f"  [RESOLVIDO] {key}")

        persistent = [v for k, v in active.items() if v.get("account_id") == account_id]
        if persistent:
            ok = _send_all(evo, whatsapps, build_persistent_summary(label, persistent))
            print(f"  [{'OK' if ok else 'FALHA'}] Resumo: {len(persistent)} persistente(s)")

        # ── Relatório diário às 08:00 (apenas no check completo) ─────────────
        if send_report:
            report_key = f"{account_id}_{today}"
            if report_key not in reports_sent:
                try:
                    insights_yesterday = get_insights_bg(account_id, yesterday)
                except Exception as e:
                    print(f"  ERRO insights ontem: {e}")
                    insights_yesterday = []
                persistent = [v for k, v in active.items() if v.get("account_id") == account_id]
                ok = _send_all(evo, whatsapps, build_daily_report(label, insights_yesterday, yesterday, persistent))
                print(f"  [{'OK' if ok else 'FALHA'}] Relatório diário ({yesterday})")
                if ok:
                    reports_sent[report_key] = now_iso

        _mark_full_check(log, account_id)

    log["active"]       = active
    log["reports_sent"] = reports_sent
    save_log(log)
    print("\nConcluído.")


if __name__ == "__main__":
    main()
