#!/usr/bin/env python3
"""
Runner de alertas Meta Ads.
Agendar via Windows Task Scheduler (setup_alertas.ps1).

Verificações a cada ciclo (30 min):
  - 70% do orçamento diário sem conversão → alerta imediato
  - 100% do orçamento diário gasto       → alerta imediato
  - CTR abaixo do mínimo                 → alerta imediato
  - CPM acima do limite                  → alerta imediato
  - Às 08:00 → relatório do dia anterior

Deduplicação: cada alerta é enviado no máximo 1x por dia por campanha.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT        = Path(__file__).parent
CONFIG_PATH = ROOT / "config_alertas.json"
LOG_PATH    = ROOT / "alertas_log.json"

# Injeta o token Meta como variável de ambiente ANTES de importar meta_api_bg,
# pois o token é lido em nível de módulo no momento do import.
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


def load_config() -> dict:
    return _CONFIG


def load_log() -> dict:
    if LOG_PATH.exists():
        with open(LOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_log(log: dict):
    cutoff = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")
    cleaned = {
        k: v for k, v in log.items()
        if k[-10:] >= cutoff
    }
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)


def is_report_window(report_time: str) -> bool:
    """Verdadeiro se estamos dentro da janela de 30 min a partir do horário do relatório."""
    now = datetime.now()
    h, m = map(int, report_time.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return 0 <= (now - target).total_seconds() < 1800


def log_tag(key: str) -> str:
    """Retorna a data no final da chave de log (últimos 10 chars)."""
    return key[-10:]


def main():
    config = load_config()
    log    = load_log()

    evo         = config["evolution_api"]
    report_time = config.get("report_time", "08:00")
    today       = datetime.today().strftime("%Y-%m-%d")
    yesterday   = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    send_report = is_report_window(report_time)

    for account in config.get("contas", []):
        account_id = account["account_id"]
        label      = account.get("label", account_id)
        whatsapp   = account["whatsapp"]
        thresholds = account.get("thresholds", {})

        print(f"\n[{label}] Iniciando verificação — {today}")

        # Busca estrutura de orçamento das campanhas
        try:
            campaigns_budget = get_campaigns_bg(account_id)
        except Exception as e:
            print(f"  ERRO ao buscar campanhas: {e}")
            campaigns_budget = []

        # ── Alertas em tempo real (dados de hoje) ─────────────────────────────
        try:
            insights_today = get_insights_bg(account_id, today)
        except Exception as e:
            print(f"  ERRO ao buscar insights hoje: {e}")
            insights_today = []

        alerts = check_alerts(insights_today, campaigns_budget, thresholds, today)
        for alert in alerts:
            if alert["key"] in log:
                continue  # já enviado hoje
            ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], whatsapp, alert["msg"])
            status = "OK" if ok else "FALHA"
            print(f"  [{status}] Alerta: {alert['key']}")
            if ok:
                log[alert["key"]] = {"ts": datetime.now().isoformat(), "msg": alert["msg"]}

        # ── Relatório diário (dados de ontem, janela das 08:00) ───────────────
        if send_report:
            report_key = f"report_{account_id}_{today}"
            if report_key not in log:
                try:
                    insights_yesterday = get_insights_bg(account_id, yesterday)
                except Exception as e:
                    print(f"  ERRO ao buscar insights ontem: {e}")
                    insights_yesterday = []

                # Alertas enviados ontem para incluir no resumo
                alerts_sent_yesterday = [
                    v for k, v in log.items()
                    if isinstance(v, dict) and "msg" in v
                    and k[-10:] == yesterday
                    and not k.startswith("report_")
                ]

                report_text = build_daily_report(label, insights_yesterday, yesterday, alerts_sent_yesterday)
                ok = send_message(evo["base_url"], evo["instance"], evo["apikey"], whatsapp, report_text)
                status = "OK" if ok else "FALHA"
                print(f"  [{status}] Relatório diário ({yesterday})")
                if ok:
                    log[report_key] = {"ts": datetime.now().isoformat(), "msg": "relatorio"}

    save_log(log)
    print("\nConcluído.")


if __name__ == "__main__":
    main()
