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
import calendar
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

from utils.meta_api_bg import (
    get_insights_bg, get_campaigns_bg,
    get_insights_for_report, get_adset_insights_for_report, get_ad_insights_for_report,
)
from utils.whatsapp    import send_message, send_document
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


def _period_dates(period_mode: str, period_days: int):
    """Calcula since/until com base no modo de período do agendamento."""
    today = datetime.today()
    if period_mode == "current_month":
        since = today.replace(day=1).strftime("%Y-%m-%d")
        until = today.strftime("%Y-%m-%d")
    elif period_mode == "previous_month":
        first_day = today.replace(day=1)
        last_day  = first_day - timedelta(days=1)
        since     = last_day.replace(day=1).strftime("%Y-%m-%d")
        until     = last_day.strftime("%Y-%m-%d")
    else:  # last_n_days
        since = (today - timedelta(days=period_days - 1)).strftime("%Y-%m-%d")
        until = today.strftime("%Y-%m-%d")
    return since, until


def _compute_next_run(sched: dict, from_dt: datetime):
    """Calcula o próximo datetime de execução após from_dt."""
    import calendar
    freq     = sched.get("frequency", "once")
    run_time = sched.get("run_at", "08:00")
    h, m     = map(int, run_time.split(":"))

    if freq == "once":
        return None
    elif freq == "daily":
        base = from_dt.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=1)
        return base.isoformat()
    elif freq == "weekly":
        dow       = sched.get("day_of_week", 0)
        base      = from_dt.replace(hour=h, minute=m, second=0, microsecond=0)
        days_fwd  = (dow - base.weekday()) % 7 or 7
        return (base + timedelta(days=days_fwd)).isoformat()
    elif freq == "monthly":
        dom        = sched.get("day_of_month", 1)
        next_month = from_dt.month % 12 + 1
        next_year  = from_dt.year + (1 if from_dt.month == 12 else 0)
        max_day    = calendar.monthrange(next_year, next_month)[1]
        base = from_dt.replace(year=next_year, month=next_month,
                               day=min(dom, max_day), hour=h, minute=m, second=0, microsecond=0)
        return base.isoformat()
    return None


def _process_schedules(config: dict):
    """Verifica e executa agendamentos de relatórios vencidos."""
    schedules = config.get("schedules", [])
    if not schedules:
        return

    try:
        from utils.report_generator import generate_report, generate_pdf_report
    except Exception as e:
        print(f"  [SCHED] Não foi possível importar report_generator: {e}")
        return

    evo     = config.get("evolution_api", {})
    now     = datetime.now()
    changed = False

    for sched in schedules:
        if not sched.get("enabled", True):
            continue
        next_run_str = sched.get("next_run")
        if not next_run_str:
            continue
        try:
            next_run_dt = datetime.fromisoformat(next_run_str)
        except Exception:
            continue
        if next_run_dt > now:
            continue

        sched_id   = sched.get("id", "?")
        account_id = sched.get("account_id", "")
        label      = next((c.get("label", account_id) for c in config.get("contas", [])
                           if c["account_id"] == account_id), account_id)
        client_name = sched.get("client_name") or label
        freq        = sched.get("frequency", "once")
        sections    = sched.get("sections", ["Visão Geral"])
        notes       = sched.get("notes", "")
        fmt         = sched.get("format", "pdf")
        recipients  = sched.get("recipients", [])
        period_mode = sched.get("period_mode", "last_n_days")
        period_days = sched.get("period_days", 30)

        print(f"\n[SCHED:{sched_id[:8]}] {label} — {freq} @ {next_run_str[:16]}")

        since, until = _period_dates(period_mode, period_days)

        try:
            df = get_insights_for_report(account_id, since, until)
        except Exception as e:
            print(f"  ERRO insights: {e}")
            sched["last_run"] = now.isoformat()
            sched["next_run"] = _compute_next_run(sched, now)
            if freq == "once":
                sched["enabled"] = False
            changed = True
            continue

        if df.empty:
            print(f"  [SCHED] Sem dados para {since}→{until}, pulando.")
            sched["last_run"] = now.isoformat()
            sched["next_run"] = _compute_next_run(sched, now)
            if freq == "once":
                sched["enabled"] = False
            changed = True
            continue

        df_prev   = df.iloc[0:0].copy()  # relatório sem comparação
        df_adsets = None
        df_ads      = None

        needs_adsets = any(s in sections for s in ("Alertas e Sugestões", "Conjuntos de Anúncios"))
        if needs_adsets:
            try:
                df_adsets = get_adset_insights_for_report(account_id, since, until)
            except Exception:
                df_adsets = None

        if "Criativos" in sections:
            try:
                df_ads = get_ad_insights_for_report(account_id, since, until)
            except Exception:
                df_ads = None

        try:
            html = generate_report(
                df=df, df_prev=df_prev, client_name=client_name,
                since=since, until=until, sections=sections, notes=notes,
                df_adsets=df_adsets, df_ads=df_ads,
            )
        except Exception as e:
            print(f"  ERRO generate_report: {e}")
            sched["last_run"] = now.isoformat()
            sched["next_run"] = _compute_next_run(sched, now)
            if freq == "once":
                sched["enabled"] = False
            changed = True
            continue

        pdf_bytes = None
        if fmt in ("pdf", "both"):
            try:
                pdf_bytes = generate_pdf_report(
                    df=df, df_prev=df_prev, client_name=client_name,
                    since=since, until=until, sections=sections, notes=notes,
                    df_adsets=df_adsets, df_ads=df_ads,
                )
            except Exception:
                pdf_bytes = None

        base_name = f"relatorio_{client_name.lower().replace(' ', '_')}_{since}_{until}"
        caption   = f"📊 Relatório Meta Ads — {client_name}\n📅 {since} a {until}"
        nums      = [n.lstrip("+").replace(" ", "").replace("-", "") for n in recipients if n]

        sent_any = False
        for num in nums:
            # Envia PDF se disponível e solicitado
            if pdf_bytes and fmt in ("pdf", "both"):
                ok = send_document(evo["base_url"], evo["instance"], evo["apikey"],
                                   num, pdf_bytes, f"{base_name}.pdf", caption)
                print(f"  [PDF→{num}] {'OK' if ok else 'FALHA'}")
                sent_any = sent_any or ok

            # Envia HTML se solicitado (ou como fallback se PDF falhou)
            if fmt in ("html", "both") or (fmt == "pdf" and not pdf_bytes):
                html_bytes = html.encode("utf-8")
                ok = send_document(evo["base_url"], evo["instance"], evo["apikey"],
                                   num, html_bytes, f"{base_name}.html", caption)
                print(f"  [HTML→{num}] {'OK' if ok else 'FALHA'}")
                sent_any = sent_any or ok

        sched["last_run"] = now.isoformat()
        sched["next_run"] = _compute_next_run(sched, now)
        if freq == "once":
            sched["enabled"] = False
        changed = True
        print(f"  [SCHED] Concluído. Próxima: {sched.get('next_run', 'N/A')}")

    if changed:
        config["schedules"] = schedules
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [SCHED] Erro ao salvar config: {e}")


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

    _process_schedules(config)
    print("\nConcluído.")


if __name__ == "__main__":
    main()
