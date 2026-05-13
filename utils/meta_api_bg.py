"""
Meta API — versão standalone sem Streamlit.
Usada pelo alertas_runner.py (script de background).
Lê o token de .streamlit/secrets.toml ou da variável de ambiente META_ACCESS_TOKEN.
"""
import os
import requests
from pathlib import Path

API_VERSION = "v20.0"
BASE_URL    = f"https://graph.facebook.com/{API_VERSION}"

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

INSIGHT_FIELDS = ",".join([
    "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "spend", "clicks", "ctr", "cpc", "cpm",
    "actions", "action_values",
])


def _load_toml(path: str) -> dict:
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (ImportError, AttributeError):
        pass
    try:
        import tomli
        with open(path, "rb") as f:
            return tomli.load(f)
    except ImportError:
        pass
    # Fallback: parser simples para secrets.toml com formato KEY = "VALUE"
    result = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#") and not line.startswith("["):
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _read_token() -> str:
    token = os.getenv("META_ACCESS_TOKEN")
    if token:
        return token
    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        secrets = _load_toml(str(secrets_path))
        token = secrets.get("META_ACCESS_TOKEN")
        if token:
            return token
    raise ValueError(
        "META_ACCESS_TOKEN não encontrado. "
        "Configure em .streamlit/secrets.toml ou na variável de ambiente META_ACCESS_TOKEN."
    )


ACCESS_TOKEN = _read_token()


def _api_get(url: str, params: dict) -> dict:
    params["access_token"] = ACCESS_TOKEN
    r = requests.get(url, params=params, timeout=30)
    data = r.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
    return data


def _paginate(response: dict) -> list:
    results = response.get("data", [])
    data = response
    while "paging" in data and "next" in data.get("paging", {}):
        data = requests.get(data["paging"]["next"], timeout=30).json()
        results.extend(data.get("data", []))
    return results


def get_insights_bg(account_id: str, date_str: str) -> list:
    """Insights de campanhas para uma data específica (nível campanha, agregado)."""
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": INSIGHT_FIELDS,
        "time_range": f'{{"since":"{date_str}","until":"{date_str}"}}',
        "level": "campaign",
        "time_increment": "all_days",
        "limit": 500,
    })
    return _process_raw(_paginate(data))


def get_campaigns_bg(account_id: str) -> list:
    """Campanhas com orçamento diário/vitalício (para calcular % gasto)."""
    data = _api_get(f"{BASE_URL}/{account_id}/campaigns", {
        "fields": "id,name,status,objective,daily_budget,lifetime_budget",
        "limit": 200,
    })
    return [c for c in _paginate(data) if c.get("status") not in ("DELETED", "ARCHIVED")]


def _process_raw(raw: list) -> list:
    rows = []
    for r in raw:
        actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
        leads = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
        conversations = (
            actions.get("onsite_conversion.messaging_conversation_started_7d", 0)
            or actions.get("onsite_conversion.messaging_first_reply", 0)
        )
        spend = float(r.get("spend", 0))
        rows.append({
            "campaign_id":   r.get("campaign_id"),
            "campaign_name": r.get("campaign_name"),
            "objective":     r.get("objective", ""),
            "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
            "spend":         spend,
            "impressions":   int(r.get("impressions", 0)),
            "clicks":        int(r.get("clicks", 0)),
            "ctr":           float(r.get("ctr", 0)),
            "cpm":           float(r.get("cpm", 0)),
            "leads":         leads,
            "conversations": conversations,
        })
    return rows
