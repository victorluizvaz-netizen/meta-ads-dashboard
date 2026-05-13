#!/usr/bin/env python3
"""
Runner de alertas Meta Ads.
Agendar via Windows Task Scheduler (setup_alertas.ps1).

Lógica de notificação:
  - Alerta NOVO (condição apareceu agora)       → envia mensagem completa imediatamente
  - Alerta PERSISTENTE (já foi notificado antes) → atualiza timestamp, sem reenvio
  - Alerta RESOLVIDO (condição sumiu)            → remove do registro silenciosamente
  - Às 08:00 → relatório do dia anterior + lista de alertas persistentes
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
from utils.alert_logic import check_alerts, build_daily_report


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


def is_report_window(report_time: str) -> bool:
    now = datetime.now()
    h, m = map(int, report_time.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return 0 <= (now - target).total_seconds() < 1800


def main():
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
        whatsapp   = account["whatsapp"]
        thresholds = account.get("thresholds", {})

        print(f"\n[{label}] Verificando — {datetime.now().strftime('%H:%M')}")

        try:
            campaigns_budget = get_campaigns_bg(account_id)
        except Exception as e:
            print(f"  ERRO campanhas: {e}")
            campaigns_budget = []

        try:
            insights_today = get_insights_bg(account_id, today)
        except Exception as e:
            print(f"  ERRO insights: {e}")
            insights_today = []

        # Condições atualmente ativas para esta conta
        current_alerts = check_alerts(insights_today, campaigns_budget, thresholds)
        current_keys   = {a["key"] for a in current_alerts}

        # ── Alertas desta conta que estavam no log ────────────────────────────
        account_active_keys = {k for k, v in active.items() if v.get("account_id") == account_id}

        # Novos: condição ativa agora mas ainda não estava no log
        for alert in current_alerts:
            if alert["key"] not in active:
                ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], whatsapp, alert["msg"])
                status = "NOVO/OK" if ok else "NOVO/FALHA"
                print(f"  [{status}] {alert['key']}")
                if ok:
                    active[alert["key"]] = {
                        "ts_first":  now_iso,
                        "ts_last":   now_iso,
                        "msg":       alert["msg"],
                        "account_id": account_id,
                        "label":     label,
                    }
            else:
                # Persistente: atualiza ts_last, não reenvia
                active[alert["key"]]["ts_last"] = now_iso
                print(f"  [PERSISTENTE] {alert['key']}")

        # Resolvidos: estavam no log desta conta mas não aparecem mais
        for key in list(account_active_keys):
            if key not in current_keys:
                del active[key]
                print(f"  [RESOLVIDO] {key}")

        # ── Relatório diário às 08:00 ─────────────────────────────────────────
        if send_report:
            report_key = f"{account_id}_{today}"
            if report_key not in reports_sent:
                try:
                    insights_yesterday = get_insights_bg(account_id, yesterday)
                except Exception as e:
                    print(f"  ERRO insights ontem: {e}")
                    insights_yesterday = []

                # Alertas ainda ativos (persistentes) desta conta para o relatório
                persistent = [v for k, v in active.items() if v.get("account_id") == account_id]

                report_text = build_daily_report(label, insights_yesterday, yesterday, persistent)
                ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], whatsapp, report_text)
                status = "OK" if ok else "FALHA"
                print(f"  [{status}] Relatório diário ({yesterday})")
                if ok:
                    reports_sent[report_key] = now_iso

    log["active"]       = active
    log["reports_sent"] = reports_sent
    save_log(log)
    print("\nConcluído.")


if __name__ == "__main__":
    main()
