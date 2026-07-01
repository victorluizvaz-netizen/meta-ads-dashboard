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
from fastapi.responses import HTMLResponse
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
    purchases = actions.get("purchase", 0) + actions.get("offsite_conversion.fb_pixel_purchase", 0)
    rev = values.get("purchase", 0) + values.get("offsite_conversion.fb_pixel_purchase", 0)
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
