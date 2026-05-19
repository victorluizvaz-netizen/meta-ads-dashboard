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

INSIGHT_FIELDS_FULL = ",".join([
    "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "frequency", "spend",
    "clicks", "unique_clicks", "ctr", "cpc", "cpm", "cpp",
    "actions", "action_values",
    "video_play_actions", "video_thruplay_watched_actions",
])

ADSET_FIELDS_FULL = ",".join([
    "adset_id", "adset_name", "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "frequency", "spend",
    "clicks", "unique_clicks", "ctr", "cpc", "cpm", "cpp",
    "actions", "action_values",
    "video_play_actions", "video_thruplay_watched_actions",
])

AD_FIELDS_FULL = ",".join([
    "ad_id", "ad_name", "adset_id", "adset_name", "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "spend",
    "clicks", "ctr", "cpc", "cpm",
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


def get_insights_for_report(account_id: str, since: str, until: str):
    """Insights completos para geração de relatório (nível campanha, granularidade diária)."""
    import pandas as pd
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": INSIGHT_FIELDS_FULL,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "campaign",
        "time_increment": 1,
        "limit": 500,
    })
    return _process_full(_paginate(data))


def get_adset_insights_for_report(account_id: str, since: str, until: str):
    """Insights de conjuntos de anúncios para relatório."""
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": ADSET_FIELDS_FULL,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "adset",
        "time_increment": "all_days",
        "limit": 500,
    })
    return _process_adset_full(_paginate(data))


def get_ad_insights_for_report(account_id: str, since: str, until: str):
    """Insights de anúncios para relatório."""
    data = _api_get(f"{BASE_URL}/{account_id}/insights", {
        "fields": AD_FIELDS_FULL,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "ad",
        "time_increment": "all_days",
        "limit": 500,
    })
    return _process_ad_full(_paginate(data))


def _process_full(raw: list):
    import pandas as pd
    if not raw:
        return pd.DataFrame()
    rows = []
    for r in raw:
        actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
        values  = {a["action_type"]: float(a["value"]) for a in r.get("action_values", [])}
        leads     = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
        purchases = actions.get("purchase", 0) + actions.get("offsite_conversion.fb_pixel_purchase", 0)
        rev       = values.get("purchase", 0) + values.get("offsite_conversion.fb_pixel_purchase", 0)
        spend     = float(r.get("spend", 0))
        conversations = (
            actions.get("onsite_conversion.messaging_conversation_started_7d", 0)
            or actions.get("onsite_conversion.messaging_first_reply", 0)
        )
        vp = r.get("video_play_actions", [])
        tp = r.get("video_thruplay_watched_actions", [])
        rows.append({
            "date":          r.get("date_start"),
            "campaign_id":   r.get("campaign_id"),
            "campaign_name": r.get("campaign_name"),
            "objective":     r.get("objective", ""),
            "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
            "impressions":   int(r.get("impressions", 0)),
            "reach":         int(r.get("reach", 0)),
            "frequency":     float(r.get("frequency", 0)),
            "spend":         spend,
            "clicks":        int(r.get("clicks", 0)),
            "unique_clicks": int(r.get("unique_clicks", 0)),
            "ctr":           float(r.get("ctr", 0)),
            "cpc":           float(r.get("cpc") or 0),
            "cpm":           float(r.get("cpm", 0)),
            "cpp":           float(r.get("cpp") or 0),
            "link_clicks":   actions.get("link_click", 0),
            "landing_page_views": actions.get("landing_page_view", 0),
            "post_engagement": actions.get("post_engagement", 0),
            "leads":         leads,
            "purchases":     purchases,
            "purchase_value": rev,
            "conversations": conversations,
            "roas":          rev / spend if spend > 0 else 0,
            "cpl":           spend / leads if leads > 0 else 0,
            "cpa":           spend / purchases if purchases > 0 else 0,
            "cpc_conv":      spend / conversations if conversations > 0 else 0,
            "video_plays":   float(vp[0]["value"]) if vp else 0,
            "thruplays":     float(tp[0]["value"]) if tp else 0,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _process_adset_full(raw: list):
    import pandas as pd
    if not raw:
        return pd.DataFrame()
    rows = []
    for r in raw:
        actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
        values  = {a["action_type"]: float(a["value"]) for a in r.get("action_values", [])}
        leads     = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
        purchases = actions.get("purchase", 0) + actions.get("offsite_conversion.fb_pixel_purchase", 0)
        rev       = values.get("purchase", 0) + values.get("offsite_conversion.fb_pixel_purchase", 0)
        spend     = float(r.get("spend", 0))
        conversations = (
            actions.get("onsite_conversion.messaging_conversation_started_7d", 0)
            or actions.get("onsite_conversion.messaging_first_reply", 0)
        )
        vp = r.get("video_play_actions", [])
        tp = r.get("video_thruplay_watched_actions", [])
        rows.append({
            "adset_id":      r.get("adset_id"),
            "adset_name":    r.get("adset_name"),
            "campaign_id":   r.get("campaign_id"),
            "campaign_name": r.get("campaign_name"),
            "objective":     r.get("objective", ""),
            "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
            "impressions":   int(r.get("impressions", 0)),
            "reach":         int(r.get("reach", 0)),
            "frequency":     float(r.get("frequency", 0)),
            "spend":         spend,
            "clicks":        int(r.get("clicks", 0)),
            "unique_clicks": int(r.get("unique_clicks", 0)),
            "ctr":           float(r.get("ctr", 0)),
            "cpc":           float(r.get("cpc") or 0),
            "cpm":           float(r.get("cpm", 0)),
            "cpp":           float(r.get("cpp") or 0),
            "link_clicks":   actions.get("link_click", 0),
            "landing_page_views": actions.get("landing_page_view", 0),
            "leads":         leads,
            "purchases":     purchases,
            "purchase_value": rev,
            "conversations": conversations,
            "roas":          rev / spend if spend > 0 else 0,
            "cpl":           spend / leads if leads > 0 else 0,
            "cpa":           spend / purchases if purchases > 0 else 0,
            "cpc_conv":      spend / conversations if conversations > 0 else 0,
            "video_plays":   float(vp[0]["value"]) if vp else 0,
            "thruplays":     float(tp[0]["value"]) if tp else 0,
        })
    return pd.DataFrame(rows)


def _process_ad_full(raw: list):
    import pandas as pd
    if not raw:
        return pd.DataFrame()
    rows = []
    for r in raw:
        actions = {a["action_type"]: float(a["value"]) for a in r.get("actions", [])}
        values  = {a["action_type"]: float(a["value"]) for a in r.get("action_values", [])}
        leads     = actions.get("lead", 0) or actions.get("onsite_conversion.lead_grouped", 0)
        purchases = actions.get("purchase", 0) + actions.get("offsite_conversion.fb_pixel_purchase", 0)
        rev       = values.get("purchase", 0) + values.get("offsite_conversion.fb_pixel_purchase", 0)
        spend     = float(r.get("spend", 0))
        conversations = (
            actions.get("onsite_conversion.messaging_conversation_started_7d", 0)
            or actions.get("onsite_conversion.messaging_first_reply", 0)
        )
        rows.append({
            "ad_id":         r.get("ad_id"),
            "ad_name":       r.get("ad_name"),
            "adset_id":      r.get("adset_id"),
            "adset_name":    r.get("adset_name"),
            "campaign_id":   r.get("campaign_id"),
            "campaign_name": r.get("campaign_name"),
            "objective":     r.get("objective", ""),
            "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
            "impressions":   int(r.get("impressions", 0)),
            "reach":         int(r.get("reach") or 0),
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
            "cpa":           spend / purchases if purchases > 0 else 0,
        })
    return pd.DataFrame(rows)


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
