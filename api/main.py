"""
FastAPI backend — Meta Ads Client Dashboard
Serves insights data for the Next.js client-facing page.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Garante que utils/ seja importável independente de onde o uvicorn é chamado
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hashlib
import hmac

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

load_dotenv(ROOT / ".env")

# ── Paths ──────────────────────────────────────────────────────────────────────
CONFIG_FILE = ROOT / "config_alertas.json"

API_VERSION = "v20.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

OBJECTIVE_MAP = {
    "BRAND_AWARENESS": "awareness", "REACH": "awareness", "OUTCOME_AWARENESS": "awareness",
    "VIDEO_VIEWS": "awareness",
    "LINK_CLICKS": "traffic", "LANDING_PAGE_VIEWS": "traffic", "OUTCOME_TRAFFIC": "traffic",
    "OUTCOME_APP_PROMOTION": "traffic",
    "LEAD_GENERATION": "leads", "OUTCOME_LEADS": "leads",
    "CONVERSIONS": "conversions", "CATALOG_SALES": "conversions",
    "PRODUCT_CATALOG_SALES": "conversions", "OUTCOME_SALES": "conversions",
    "STORE_VISITS": "conversions", "OUTCOME_ENGAGEMENT": "conversions",
}

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Meta Ads Client API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# ── Config helpers ─────────────────────────────────────────────────────────────
def _load_config() -> dict:
    # 1) arquivo local (dev)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    # 2) produção (ex.: Railway): carrega do GitHub Gist usando
    #    GITHUB_GIST_ID / GITHUB_TOKEN do ambiente (mesma config do Streamlit)
    try:
        from utils.config_loader import load_config as _shared_load
        cfg = _shared_load()
        if cfg:
            return cfg
    except Exception:
        pass
    raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")


def _find_account(token: str) -> dict | None:
    cfg = _load_config()
    for conta in cfg.get("contas", []):
        if conta.get("client_token") == token and conta.get("client_token"):
            return conta
    return None


def _meta_token() -> str:
    try:
        from utils.meta_api_bg import ACCESS_TOKEN
        if ACCESS_TOKEN:
            return ACCESS_TOKEN
    except Exception:
        pass
    token = os.getenv("META_ACCESS_TOKEN")
    if token:
        return token
    secrets_path = ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with open(secrets_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("META_ACCESS_TOKEN"):
                    _, _, val = line.partition("=")
                    return val.strip().strip('"').strip("'")
    # Produção: o token também vem no config (Gist)
    try:
        t = _load_config().get("meta_access_token", "")
        if t and t != "SEU_TOKEN_META_AQUI":
            return t
    except Exception:
        pass
    raise ValueError("META_ACCESS_TOKEN not found")


# ── Meta API helpers ───────────────────────────────────────────────────────────
def _api_get(url: str, params: dict) -> dict:
    params["access_token"] = _meta_token()
    r = requests.get(url, params=params, timeout=30)
    data = r.json()
    if "error" in data:
        raise HTTPException(status_code=502, detail=data["error"]["message"])
    return data


def _paginate(response: dict) -> list:
    results = response.get("data", [])
    data = response
    while "paging" in data and "next" in data.get("paging", {}):
        data = requests.get(data["paging"]["next"], timeout=30).json()
        results.extend(data.get("data", []))
    return results


def _process_row(r: dict) -> dict:
    actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
    values  = {a["action_type"]: float(a["value"]) for a in r.get("action_values", [])}

    leads = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
    # "purchase" já é o total oficial deduplicado do Meta; "offsite_conversion.fb_pixel_purchase"
    # é a MESMA compra vista pelo pixel, não uma fonte adicional — somar os dois dobra a contagem
    # e a receita (confirmado contra campanha real: purchase=2/R$1699,22 igual a
    # offsite_conversion.fb_pixel_purchase=2/R$1699,22, mesmas 2 compras contadas 2x).
    purchases = actions.get("purchase", 0) or actions.get("offsite_conversion.fb_pixel_purchase", 0)
    rev = values.get("purchase", 0) or values.get("offsite_conversion.fb_pixel_purchase", 0)
    spend = float(r.get("spend", 0))
    conversations = (
        actions.get("onsite_conversion.messaging_conversation_started_7d", 0)
        or actions.get("onsite_conversion.messaging_first_reply", 0)
    )
    vp = r.get("video_play_actions", [])
    tp = r.get("video_thruplay_watched_actions", [])
    imp = int(r.get("impressions", 0))
    reach = int(r.get("reach") or 0)

    return {
        "date":          r.get("date_start"),
        "campaign_id":   r.get("campaign_id"),
        "campaign_name": r.get("campaign_name"),
        "objective":     r.get("objective", ""),
        "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
        "impressions":   imp,
        "reach":         reach,
        "frequency":     float(r.get("frequency", 0)),
        "spend":         spend,
        "clicks":        int(r.get("clicks", 0)),
        "ctr":           float(r.get("ctr", 0)),
        "cpc":           float(r.get("cpc") or 0),
        "cpm":           float(r.get("cpm", 0)),
        "leads":         leads,
        "purchases":     purchases,
        "purchase_value": rev,
        "conversations": conversations,
        "roas":          rev / spend if spend > 0 else 0,
        "cpl":           spend / leads if leads > 0 else 0,
        "video_plays":   float(vp[0]["value"]) if vp else 0,
        "thruplays":     float(tp[0]["value"]) if tp else 0,
    }


INSIGHT_FIELDS = ",".join([
    "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "frequency", "spend",
    "clicks", "ctr", "cpc", "cpm",
    "actions", "action_values",
    "video_play_actions", "video_thruplay_watched_actions",
])


def _fetch_insights(account_id: str, since: str, until: str) -> list[dict]:
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": INSIGHT_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "campaign",
        "time_increment": 1,
        "limit": 500,
    })
    return [_process_row(r) for r in _paginate(data)]


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/api/validate-token")
def validate_token(token: str = Query(...)):
    """Validates client token and returns account label."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido ou acesso revogado.")
    return {
        "label":      account.get("label", account["account_id"]),
        "account_id": account["account_id"],
    }


@app.get("/api/insights")
def get_insights(
    token: str = Query(...),
    since: str = Query(...),  # YYYY-MM-DD
    until: str = Query(...),  # YYYY-MM-DD
):
    """Returns campaign insights + previous period for comparison."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")

    account_id = account["account_id"]

    # Parse dates for comparison period
    dt_since = datetime.strptime(since, "%Y-%m-%d")
    dt_until = datetime.strptime(until, "%Y-%m-%d")
    n_days = (dt_until - dt_since).days + 1
    prev_until = dt_since - timedelta(days=1)
    prev_since = prev_until - timedelta(days=n_days - 1)

    current = _fetch_insights(account_id, since, until)
    previous = _fetch_insights(account_id, prev_since.strftime("%Y-%m-%d"), prev_until.strftime("%Y-%m-%d"))

    return {
        "current":    current,
        "previous":   previous,
        "prev_since": prev_since.strftime("%Y-%m-%d"),
        "prev_until": prev_until.strftime("%Y-%m-%d"),
        "n_days":     n_days,
    }


@app.get("/api/campaigns")
def get_campaigns(token: str = Query(...)):
    """Returns the account's campaigns (id, name, status) for the client token.
    Scoped strictly to the token's account — a client can only see their own."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")

    account_id = account["account_id"]
    data = _api_get(f"{BASE_URL}/{account_id}/campaigns", {
        "fields": "id,name,status,effective_status,objective",
        "limit": 200,
    })
    campaigns = [
        {
            "id":               c["id"],
            "name":             c.get("name", ""),
            "status":           c.get("status", ""),
            "effective_status": c.get("effective_status", c.get("status", "")),
            "objective":        c.get("objective", ""),
        }
        for c in _paginate(data)
        if c.get("status") not in ("DELETED", "ARCHIVED")
    ]
    return {"campaigns": campaigns}


# ── Config de saldo/cobrança + saldo da conta (client token) ────────────────────
# Mesmos campos que utils/alert_logic.py::check_saldo já lê de config_alertas.json
# (rodado por alertas_runner.py) — essas rotas deixam o Pulso editar/ler os MESMOS
# campos remotamente, sem duplicar o dado em outro lugar.
#
# Sem flag de "prepago/pospago": o "disponível" é sempre spend_cap - amount_spent
# quando a conta tem spend_cap configurado (é assim que o pré-pago funciona na
# prática aqui — depósito PIX vira um aumento do spend_cap, não um saldo
# separado). Uma flag manual pra isso existiu numa versão anterior e causou um
# alerta errado (usava 'balance', que é fatura em aberto, não saldo) — removida.

class AccountConfigBody(BaseModel):
    saldo_minimo: float | None = None


@app.get("/api/account-config")
def get_account_config(token: str = Query(...)):
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")
    return {
        "saldo_minimo": (account.get("thresholds") or {}).get("saldo_minimo"),
    }


@app.post("/api/account-config")
def save_account_config(body: AccountConfigBody, token: str = Query(...)):
    """Só altera saldo_minimo da conta do próprio token — nunca mexe em
    account_id/client_token/whatsapp/outras contas (por isso o corpo é validado
    por um BaseModel restrito, não um dict genérico como /admin/config usa)."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")
    cfg = _load_config()
    for conta in cfg.get("contas", []):
        if conta.get("client_token") == token:
            conta.setdefault("thresholds", {})["saldo_minimo"] = body.saldo_minimo
            break
    from utils.config_loader import save_config
    save_config(cfg)
    return {"success": True}


@app.get("/api/account-balance")
def get_account_balance(token: str = Query(...)):
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")
    return _api_get(f"{BASE_URL}/{account['account_id']}", {
        "fields": "name,currency,balance,spend_cap,amount_spent,account_status",
    })


# ── Detalhe de campanha (client token) ──────────────────────────────────────────
GENDER_MAP = {"1": "Masculino", "2": "Feminino", 1: "Masculino", 2: "Feminino",
              "male": "Masculino", "female": "Feminino", "unknown": "Não informado"}

BREAKDOWN_MAP = {
    "age_gender": "age,gender",
    "region":     "region",
    "device":     "impression_device",
    "platform":   "publisher_platform",
}


def _budget_reais(v) -> float | None:
    """Orçamentos vêm em centavos (string). Converte para reais."""
    try:
        f = float(v)
        return f / 100.0 if f > 0 else None
    except (TypeError, ValueError):
        return None


def _require_campaign(token: str, campaign_id: str) -> dict:
    """Valida o token e garante que a campanha pertence à conta do token (anti-IDOR).
    Impede que um cliente leia dados de campanha de outra conta passando outro id."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")
    acct = str(account["account_id"]).replace("act_", "")
    try:
        info = _api_get(f"{BASE_URL}/{campaign_id}", {"fields": "account_id"})
    except HTTPException:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    if str(info.get("account_id")) != acct:
        raise HTTPException(status_code=403, detail="Campanha não pertence a esta conta.")
    return account


def _summarize_targeting(adsets: list[dict]) -> dict:
    """Consolida o público CONFIGURADO a partir do targeting dos conjuntos."""
    age_min = age_max = None
    genders, countries, regions, cities = set(), set(), set(), set()
    device_platforms, publisher_platforms, user_os, interests, opt_goals = set(), set(), set(), set(), set()
    for a in adsets:
        t = a.get("targeting", {}) or {}
        if t.get("age_min"):
            age_min = min(age_min, t["age_min"]) if age_min else t["age_min"]
        if t.get("age_max"):
            age_max = max(age_max, t["age_max"]) if age_max else t["age_max"]
        for g in t.get("genders", []) or []:
            genders.add(GENDER_MAP.get(str(g), str(g)))
        geo = t.get("geo_locations", {}) or {}
        for cc in geo.get("countries", []) or []:
            countries.add(cc)
        for r in geo.get("regions", []) or []:
            if r.get("name"):
                regions.add(r["name"])
        for cy in geo.get("cities", []) or []:
            if cy.get("name"):
                cities.add(cy["name"])
        for d in t.get("device_platforms", []) or []:
            device_platforms.add(d)
        for p in t.get("publisher_platforms", []) or []:
            publisher_platforms.add(p)
        for o in t.get("user_os", []) or []:
            user_os.add(o)
        for spec in t.get("flexible_spec", []) or []:
            for it in spec.get("interests", []) or []:
                if it.get("name"):
                    interests.add(it["name"])
        for it in t.get("interests", []) or []:
            if isinstance(it, dict) and it.get("name"):
                interests.add(it["name"])
        if a.get("optimization_goal"):
            opt_goals.add(a["optimization_goal"])
    return {
        "age_min": age_min, "age_max": age_max,
        "genders": sorted(genders),
        "countries": sorted(countries), "regions": sorted(regions), "cities": sorted(cities),
        "device_platforms": sorted(device_platforms),
        "publisher_platforms": sorted(publisher_platforms),
        "user_os": sorted(user_os),
        "interests": sorted(interests)[:30],
        "optimization_goals": sorted(opt_goals),
        "adset_count": len(adsets),
    }


@app.get("/api/campaign-overview")
def campaign_overview(
    token: str = Query(...),
    campaign_id: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
):
    """Visão geral da campanha: objetivo, status, orçamento, público configurado
    e totais de desempenho no período. Escopo travado na conta do token."""
    _require_campaign(token, campaign_id)
    camp = _api_get(f"{BASE_URL}/{campaign_id}", {
        "fields": "name,objective,status,effective_status,daily_budget,lifetime_budget",
    })
    ad = _api_get(f"{BASE_URL}/{campaign_id}/adsets", {
        "fields": "name,status,daily_budget,lifetime_budget,optimization_goal,targeting",
        "limit": 100,
    })
    adsets = [a for a in _paginate(ad) if a.get("status") not in ("DELETED", "ARCHIVED")]
    targeting = _summarize_targeting(adsets)
    adsets_daily = sum(_budget_reais(a.get("daily_budget")) or 0 for a in adsets)
    adsets_lifetime = sum(_budget_reais(a.get("lifetime_budget")) or 0 for a in adsets)
    ins = _api_get(f"{BASE_URL}/{campaign_id}/insights", {
        "fields": INSIGHT_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
    })
    rows = ins.get("data", [])
    totals = _process_row(rows[0]) if rows else {}
    return {
        "campaign": {
            "id": campaign_id,
            "name": camp.get("name", ""),
            "objective": camp.get("objective", ""),
            "objective_group": OBJECTIVE_MAP.get(camp.get("objective", ""), "other"),
            "status": camp.get("status", ""),
            "effective_status": camp.get("effective_status", camp.get("status", "")),
        },
        "budget": {
            "campaign_daily": _budget_reais(camp.get("daily_budget")),
            "campaign_lifetime": _budget_reais(camp.get("lifetime_budget")),
            "adsets_daily": adsets_daily or None,
            "adsets_lifetime": adsets_lifetime or None,
        },
        "targeting": targeting,
        "totals": totals,
    }


@app.get("/api/campaign-breakdown")
def campaign_breakdown(
    token: str = Query(...),
    campaign_id: str = Query(...),
    dim: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
):
    """Insights da campanha segmentados por uma dimensão demográfica/técnica:
    age_gender | region | device | platform. Escopo travado na conta do token."""
    if dim not in BREAKDOWN_MAP:
        raise HTTPException(status_code=400, detail="Dimensão inválida.")
    _require_campaign(token, campaign_id)
    data = _api_get(f"{BASE_URL}/{campaign_id}/insights", {
        "fields": "impressions,clicks,spend,ctr,cpc,cpm,reach,actions",
        "breakdowns": BREAKDOWN_MAP[dim],
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "limit": 500,
    })
    rows = []
    for r in _paginate(data):
        actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
        leads = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
        row = {
            "impressions": int(r.get("impressions", 0)),
            "clicks": int(r.get("clicks", 0)),
            "spend": float(r.get("spend", 0)),
            "ctr": float(r.get("ctr", 0)),
            "cpc": float(r.get("cpc") or 0),
            "cpm": float(r.get("cpm", 0)),
            "leads": leads,
        }
        if dim == "age_gender":
            row["age"] = r.get("age", "")
            row["gender"] = GENDER_MAP.get(str(r.get("gender")), r.get("gender", ""))
        elif dim == "region":
            row["region"] = r.get("region", "")
        elif dim == "device":
            row["device"] = r.get("impression_device", "")
        elif dim == "platform":
            row["platform"] = r.get("publisher_platform", "")
        rows.append(row)
    rows.sort(key=lambda x: x["impressions"], reverse=True)
    return {"dim": dim, "rows": rows}


_REPORT_SECTIONS_BY_TYPE = {
    "awareness":   ["Awareness"],
    "traffic":     ["Tráfego"],
    "leads":       ["Leads"],
    "conversions": ["Conversões"],
}


@app.get("/api/campaign-report")
def campaign_report(
    token: str = Query(...),
    campaign_id: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
    format: str = Query("pdf"),
):
    """Relatório de UMA campanha (PDF ou HTML), com seções adaptadas ao objetivo
    dela (ex: campanha de awareness não leva seção de Leads/Conversões). Reaproveita
    o gerador de relatório do admin (utils/report_generator.py) e os fetchers
    Streamlit-free de utils/meta_api_bg.py — nenhuma lógica de cálculo duplicada.
    Escopo travado na conta do token via _require_campaign (anti-IDOR)."""
    import pandas as pd
    from utils.meta_api_bg import (
        get_insights_for_report, get_adset_insights_for_report,
        get_ad_insights_for_report, get_ad_creatives_bg,
    )
    from utils.report_generator import generate_pdf_report, generate_report

    account = _require_campaign(token, campaign_id)
    account_id = account["account_id"]

    df = get_insights_for_report(account_id, since, until)
    df = df[df["campaign_id"] == campaign_id] if not df.empty else df
    if df.empty:
        raise HTTPException(status_code=404, detail="Sem dados para essa campanha no período.")
    df_prev = pd.DataFrame()

    df_adsets = get_adset_insights_for_report(account_id, since, until)
    df_adsets = df_adsets[df_adsets["campaign_id"] == campaign_id] if not df_adsets.empty else df_adsets

    df_ads = get_ad_insights_for_report(account_id, since, until)
    df_ads = df_ads[df_ads["campaign_id"] == campaign_id] if not df_ads.empty else df_ads
    if not df_ads.empty:
        creatives = get_ad_creatives_bg(df_ads["ad_id"].dropna().unique().tolist())
        df_ads["thumbnail_url"] = df_ads["ad_id"].map(lambda i: creatives.get(i, {}).get("thumbnail_url"))
        df_ads["preview_link"] = df_ads["ad_id"].map(lambda i: creatives.get(i, {}).get("preview_shareable_link"))
        df_ads["library_link"] = df_ads["ad_id"].map(
            lambda i: (
                f"https://www.facebook.com/ads/library/?view_all_page_id={creatives.get(i, {}).get('page_id')}"
                if creatives.get(i, {}).get("page_id") else None
            )
        )

    campaign_type = df["campaign_type"].iloc[0]
    sections = ["Visão Geral"] + _REPORT_SECTIONS_BY_TYPE.get(campaign_type, []) + ["Conjuntos de Anúncios", "Criativos"]
    client_name = account.get("name") or "Cliente"

    if format == "html":
        html = generate_report(df, df_prev, client_name, since, until, sections,
                                df_adsets=df_adsets, df_ads=df_ads)
        return HTMLResponse(html)

    pdf_bytes = generate_pdf_report(df, df_prev, client_name, since, until, sections,
                                     df_adsets=df_adsets, df_ads=df_ads)
    return Response(content=pdf_bytes, media_type="application/pdf",
                     headers={"Content-Disposition": 'attachment; filename="relatorio.pdf"'})


@app.get("/api/leads")
def campaign_leads(
    token: str = Query(...),
    campaign_id: str = Query(...),
    since: str = Query(None),
):
    """Leads individuais (nome/telefone/e-mail + respostas do formulário) das ads
    da campanha. Escopo travado na conta do token (mesma trava anti-IDOR de
    campaign-overview/campaign-breakdown, via _require_campaign).

    A API de leads do Meta funciona por AD, não por campanha direto — busca todas
    as ads da campanha e agrega o edge /leads de cada uma. Exige a permissão
    leads_retrieval (+ ads_read) no token de acesso (META_ACCESS_TOKEN); sem ela,
    toda ad falha e o erro real do Meta é propagado (não vira lista vazia sem
    explicação — importante pra diagnosticar a falta da permissão)."""
    _require_campaign(token, campaign_id)
    ads_data = _api_get(f"{BASE_URL}/{campaign_id}/ads", {"fields": "id", "limit": 200})
    ad_ids = [a["id"] for a in _paginate(ads_data)]

    since_dt = None
    if since:
        try:
            # 'since' vem naive (hora de Brasília) do lado do Pulso; created_time do
            # Meta vem em UTC — comparação aproximada (~3h de folga), suficiente pra
            # limitar o tamanho da resposta. O dedupe de verdade é por lead, no Pulso.
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            since_dt = None

    leads: list[dict] = []
    any_success = False
    last_error: HTTPException | None = None
    for ad_id in ad_ids:
        try:
            data = _api_get(f"{BASE_URL}/{ad_id}/leads", {"fields": "id,created_time,field_data", "limit": 200})
            any_success = True
        except HTTPException as e:
            last_error = e
            continue  # ad sem formulário de lead vinculado costuma dar erro aqui — ignora e segue
        for lead in _paginate(data):
            if since_dt:
                try:
                    created = datetime.strptime(lead["created_time"], "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
                    if created < since_dt:
                        continue
                except (KeyError, ValueError):
                    pass
            leads.append(lead)

    # Só propaga o erro se NENHUMA ad respondeu (ex.: permissão leads_retrieval
    # ausente) — se algumas ads não tinham formulário de lead, isso é normal.
    if ad_ids and not any_success and last_error is not None:
        raise last_error

    leads.sort(key=lambda l: l.get("created_time", ""), reverse=True)
    return {"leads": leads}


# ── Pixel de conversão (client token) ───────────────────────────────────────────
# Uma conta pode ter vários pixels (confirmado contra conta real: uma tinha 4,
# com nomes parecidos) — não existe um jeito de saber automaticamente qual pixel
# corresponde a qual campanha, então o Pulso deixa o admin escolher manualmente
# por card (mesmo padrão de meta_campaign_id), usando /api/pixels pra listar as
# opções com um sinal de qual é o certo (contagem de eventos Lead recentes).
def _require_pixel(token: str, pixel_id: str) -> dict:
    """Anti-IDOR: confere que o pixel pedido pertence à conta do token. Não existe
    um campo direto "esse pixel é dessa conta?" na Graph API — só dá pra conferir
    listando os pixels da conta e comparando o id (mesma ideia de _require_campaign)."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")
    pixels_data = _api_get(f"{BASE_URL}/{account['account_id']}/adspixels", {"fields": "id"})
    pixel_ids = {p["id"] for p in _paginate(pixels_data)}
    if pixel_id not in pixel_ids:
        raise HTTPException(status_code=403, detail="Pixel não pertence a esta conta.")
    return account


@app.get("/api/pixels")
def list_pixels(token: str = Query(...)):
    """Pixels da conta do token, com last_fired_time + volume de eventos Lead dos
    últimos 7 dias (sinal pra ajudar o admin a diferenciar pixels com nome parecido)."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")
    data = _api_get(f"{BASE_URL}/{account['account_id']}/adspixels", {
        "fields": "id,name,last_fired_time",
    })
    pixels = _paginate(data)
    now = datetime.utcnow()
    since = int((now - timedelta(days=7)).timestamp())
    until = int(now.timestamp())
    for p in pixels:
        try:
            stats = _api_get(f"{BASE_URL}/{p['id']}/stats", {
                "aggregation": "event", "start_time": since, "end_time": until,
            })
            p["lead_count_7d"] = sum(
                ev.get("count", 0)
                for bucket in stats.get("data", [])
                for ev in bucket.get("data", [])
                if ev.get("value") == "Lead"
            )
        except Exception:
            p["lead_count_7d"] = None
    return {"pixels": pixels}


@app.get("/api/pixel-stats")
def pixel_stats(token: str = Query(...), pixel_id: str = Query(...), days: int = Query(7)):
    """Volume de eventos do pixel por tipo, últimos `days` dias — mesma agregação
    que o Gerenciador de Eventos do Meta mostra.

    `buckets` (por hora, cru) vem junto pra quem precisa detectar "evento novo desde
    a última checagem" (ex.: alerta de Purchase no alert_engine.py do Pulso) — a API
    de pixel não dá id individual por evento, só contagem agregada por hora, então é
    o granular máximo disponível pra dedupe."""
    _require_pixel(token, pixel_id)
    info = _api_get(f"{BASE_URL}/{pixel_id}", {"fields": "id,name,last_fired_time"})
    now = datetime.utcnow()
    since = int((now - timedelta(days=days)).timestamp())
    until = int(now.timestamp())
    stats = _api_get(f"{BASE_URL}/{pixel_id}/stats", {
        "aggregation": "event", "start_time": since, "end_time": until,
    })
    totals: dict[str, int] = {}
    buckets = []
    for bucket in stats.get("data", []):
        bucket_events = {}
        for ev in bucket.get("data", []):
            name = ev.get("value") or "Desconhecido"
            totals[name] = totals.get(name, 0) + ev.get("count", 0)
            bucket_events[name] = bucket_events.get(name, 0) + ev.get("count", 0)
        buckets.append({"start_time": bucket.get("start_time"), "events": bucket_events})
    events = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "id": info.get("id"),
        "name": info.get("name"),
        "last_fired_time": info.get("last_fired_time"),
        "events": [{"name": n, "count": c} for n, c in events],
        "buckets": buckets,
    }


@app.get("/api/adsets")
def get_adsets(token: str = Query(...)):
    """Returns adsets list for the account."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")

    account_id = account["account_id"]
    data = _api_get(f"{BASE_URL}/{account_id}/adsets", {
        "fields": "id,name,status,campaign_id,campaign_name,targeting,optimization_goal,bid_strategy,daily_budget,lifetime_budget,billing_event",
        "limit": 200,
    })
    adsets = [a for a in _paginate(data) if a.get("status") not in ("DELETED", "ARCHIVED")]
    return {"adsets": adsets}


AD_INSIGHT_FIELDS = ",".join([
    "ad_id", "ad_name", "adset_id", "adset_name",
    "campaign_id", "campaign_name", "objective",
    "impressions", "spend", "clicks", "ctr", "cpc", "cpm",
    "actions",
])


def _process_ad_row(r: dict) -> dict:
    actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
    leads = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
    conversations = (
        actions.get("onsite_conversion.messaging_conversation_started_7d", 0)
        or actions.get("onsite_conversion.messaging_first_reply", 0)
    )
    spend  = float(r.get("spend", 0))
    imp    = int(r.get("impressions", 0))
    clicks = int(r.get("clicks", 0))
    return {
        "ad_id":        r.get("ad_id"),
        "ad_name":      r.get("ad_name", ""),
        "adset_id":     r.get("adset_id"),
        "adset_name":   r.get("adset_name", ""),
        "campaign_id":  r.get("campaign_id"),
        "campaign_name": r.get("campaign_name", ""),
        "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
        "spend":         spend,
        "impressions":   imp,
        "clicks":        clicks,
        "leads":         leads,
        "conversations": conversations,
        "ctr":           float(r.get("ctr", 0)),
        "cpc":           float(r.get("cpc") or 0),
        "cpm":           float(r.get("cpm", 0)),
        "cpl":           spend / leads if leads > 0 else 0,
    }


@app.get("/api/ads")
def get_ads(
    token: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
):
    """Returns ad-level insights aggregated over the period."""
    account = _find_account(token)
    if not account:
        raise HTTPException(status_code=401, detail="Token inválido.")

    account_id = account["account_id"]
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": AD_INSIGHT_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "ad",
        "limit": 500,
    })

    raw = [_process_ad_row(r) for r in _paginate(data)]

    # Aggregate by ad_id (API may return daily rows depending on breakdowns)
    ad_map: dict[str, dict] = {}
    for r in raw:
        key = r["ad_id"] or r["ad_name"]
        if key not in ad_map:
            ad_map[key] = {**r}
        else:
            a = ad_map[key]
            a["spend"]         += r["spend"]
            a["impressions"]   += r["impressions"]
            a["clicks"]        += r["clicks"]
            a["leads"]         += r["leads"]
            a["conversations"] += r["conversations"]

    ads = []
    for a in ad_map.values():
        imp    = a["impressions"]
        clicks = a["clicks"]
        spend  = a["spend"]
        leads  = a["leads"]
        a["ctr"] = clicks / imp * 100    if imp    > 0 else 0
        a["cpm"] = spend  / imp * 1000   if imp    > 0 else 0
        a["cpc"] = spend  / clicks       if clicks > 0 else 0
        a["cpl"] = spend  / leads        if leads  > 0 else 0
        ads.append(a)

    ads.sort(key=lambda x: x["spend"], reverse=True)
    return {"ads": ads}


# ── Admin auth ─────────────────────────────────────────────────────────────────
def _admin_password() -> str:
    try:
        cfg = _load_config()
        pwd = cfg.get("dashboard_password", "")
    except Exception:
        pwd = ""
    return pwd or os.getenv("ADMIN_PASSWORD", "")


def _admin_token(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest() if password else "no-auth"


def _check_admin(x_admin_token: str | None) -> None:
    pwd = _admin_password()
    if not pwd:
        return  # no password configured = open access
    expected = _admin_token(pwd)
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Token de admin inválido.")


class LoginBody(BaseModel):
    password: str


@app.post("/admin/login")
def admin_login(body: LoginBody):
    pwd = _admin_password()
    if not pwd or body.password == pwd:
        return {"token": _admin_token(pwd), "no_password": not pwd}
    raise HTTPException(status_code=401, detail="Senha incorreta.")


@app.get("/admin/accounts")
def admin_accounts(x_admin_token: str | None = Header(default=None)):
    _check_admin(x_admin_token)
    cfg = _load_config()
    return {
        "accounts": [
            {"account_id": c["account_id"], "label": c.get("label", c["account_id"])}
            for c in cfg.get("contas", [])
        ]
    }


@app.get("/admin/insights")
def admin_insights(
    account_id: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    dt_since = datetime.strptime(since, "%Y-%m-%d")
    dt_until = datetime.strptime(until, "%Y-%m-%d")
    n_days   = (dt_until - dt_since).days + 1
    prev_until = dt_since - timedelta(days=1)
    prev_since = prev_until - timedelta(days=n_days - 1)

    current  = _fetch_insights(account_id, since, until)
    previous = _fetch_insights(account_id, prev_since.strftime("%Y-%m-%d"), prev_until.strftime("%Y-%m-%d"))

    return {
        "current":    current,
        "previous":   previous,
        "prev_since": prev_since.strftime("%Y-%m-%d"),
        "prev_until": prev_until.strftime("%Y-%m-%d"),
        "n_days":     n_days,
    }


@app.get("/admin/ads")
def admin_ads(
    account_id: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": AD_INSIGHT_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "ad",
        "limit": 500,
    })
    raw = [_process_ad_row(r) for r in _paginate(data)]
    ad_map: dict[str, dict] = {}
    for r in raw:
        key = r["ad_id"] or r["ad_name"]
        if key not in ad_map:
            ad_map[key] = {**r}
        else:
            a = ad_map[key]
            a["spend"]         += r["spend"]
            a["impressions"]   += r["impressions"]
            a["clicks"]        += r["clicks"]
            a["leads"]         += r["leads"]
            a["conversations"] += r["conversations"]
    ads = []
    for a in ad_map.values():
        imp = a["impressions"]; clicks = a["clicks"]; spend = a["spend"]; leads = a["leads"]
        a["ctr"] = clicks / imp * 100    if imp    > 0 else 0
        a["cpm"] = spend  / imp * 1000   if imp    > 0 else 0
        a["cpc"] = spend  / clicks       if clicks > 0 else 0
        a["cpl"] = spend  / leads        if leads  > 0 else 0
        ads.append(a)
    ads.sort(key=lambda x: x["spend"], reverse=True)
    return {"ads": ads}


CAMPAIGN_FIELDS = "id,name,status,objective,daily_budget,lifetime_budget,insights{spend,impressions,clicks,leads}"


@app.get("/admin/campaigns")
def admin_campaigns(
    account_id: str = Query(...),
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    data = _api_get(f"{BASE_URL}/{account_id}/campaigns", {
        "fields": "id,name,status,objective,daily_budget,lifetime_budget",
        "limit": 200,
    })
    campaigns = [c for c in _paginate(data) if c.get("status") not in ("DELETED", "ARCHIVED")]
    return {"campaigns": campaigns}


class CampaignPatch(BaseModel):
    status: str | None = None
    daily_budget: int | None = None
    lifetime_budget: int | None = None


@app.patch("/admin/campaigns/{campaign_id}")
def admin_patch_campaign(
    campaign_id: str,
    body: CampaignPatch,
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    params: dict[str, Any] = {"access_token": _meta_token()}
    if body.status is not None:
        params["status"] = body.status
    if body.daily_budget is not None:
        params["daily_budget"] = str(body.daily_budget)
    if body.lifetime_budget is not None:
        params["lifetime_budget"] = str(body.lifetime_budget)
    r = requests.post(f"{BASE_URL}/{campaign_id}", params=params, timeout=15)
    data = r.json()
    if "error" in data:
        raise HTTPException(status_code=502, detail=data["error"]["message"])
    return {"success": data.get("success", True)}


@app.get("/admin/adsets")
def admin_adsets(
    account_id: str = Query(...),
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    data = _api_get(f"{BASE_URL}/{account_id}/adsets", {
        "fields": "id,name,status,campaign_id,campaign_name,optimization_goal,bid_strategy,daily_budget,lifetime_budget,billing_event,targeting",
        "limit": 200,
    })
    adsets = [a for a in _paginate(data) if a.get("status") not in ("DELETED", "ARCHIVED")]
    return {"adsets": adsets}


@app.patch("/admin/adsets/{adset_id}")
def admin_patch_adset(
    adset_id: str,
    body: CampaignPatch,
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    params: dict[str, Any] = {"access_token": _meta_token()}
    if body.status is not None:
        params["status"] = body.status
    if body.daily_budget is not None:
        params["daily_budget"] = str(body.daily_budget)
    if body.lifetime_budget is not None:
        params["lifetime_budget"] = str(body.lifetime_budget)
    r = requests.post(f"{BASE_URL}/{adset_id}", params=params, timeout=15)
    data = r.json()
    if "error" in data:
        raise HTTPException(status_code=502, detail=data["error"]["message"])
    return {"success": data.get("success", True)}


@app.get("/admin/config")
def admin_config(x_admin_token: str | None = Header(default=None)):
    _check_admin(x_admin_token)
    cfg = _load_config()
    safe = {k: v for k, v in cfg.items() if k not in ("github_token", "meta_access_token")}
    return safe


@app.post("/admin/config")
def admin_save_config(
    body: dict,
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    try:
        from utils.config_loader import save_config
        cfg = _load_config()
        cfg.update({k: v for k, v in body.items() if k not in ("github_token", "meta_access_token")})
        save_config(cfg)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/report", response_class=HTMLResponse)
def admin_report(
    account_id: str = Query(...),
    since: str = Query(...),
    until: str = Query(...),
    client_name: str = Query(default="Cliente"),
    sections: str = Query(default="Visão Geral,Awareness,Tráfego,Leads,Conversões"),
    notes: str = Query(default=""),
    x_admin_token: str | None = Header(default=None),
):
    _check_admin(x_admin_token)
    try:
        import pandas as pd
        from utils.report_generator import generate_report

        sections_list = [s.strip() for s in sections.split(",") if s.strip()]

        dt_since = datetime.strptime(since, "%Y-%m-%d")
        dt_until = datetime.strptime(until, "%Y-%m-%d")
        n_days = (dt_until - dt_since).days + 1
        prev_until = dt_since - timedelta(days=1)
        prev_since = prev_until - timedelta(days=n_days - 1)

        rows = _fetch_insights(account_id, since, until)
        rows_prev = _fetch_insights(account_id, prev_since.strftime("%Y-%m-%d"), prev_until.strftime("%Y-%m-%d"))

        if not rows:
            return HTMLResponse("<h1>Sem dados para o período.</h1>", status_code=200)

        df = pd.DataFrame(rows)
        df_prev = pd.DataFrame(rows_prev) if rows_prev else pd.DataFrame()

        html = generate_report(
            df=df, df_prev=df_prev,
            client_name=client_name,
            since=since, until=until,
            sections=sections_list,
            notes=notes,
            df_adsets=None, df_ads=None, adsets_config=None,
        )
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}
