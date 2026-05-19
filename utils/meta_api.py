import requests
import pandas as pd
import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def _secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

ACCESS_TOKEN = _secret("META_ACCESS_TOKEN")
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

METRIC_LABELS = {
    "spend": "Investimento",
    "impressions": "Impressões",
    "reach": "Alcance",
    "frequency": "Frequência",
    "clicks": "Cliques",
    "ctr": "Taxa de Cliques (CTR)",
    "cpc": "Custo por Clique (CPC)",
    "cpm": "Custo por 1.000 Impressões (CPM)",
    "leads": "Leads",
    "cpl": "Custo por Lead (CPL)",
    "purchases": "Compras",
    "purchase_value": "Receita",
    "roas": "Retorno sobre Investimento (ROAS)",
    "cpa": "Custo por Aquisição (CPA)",
    "video_plays": "Reproduções de Vídeo",
    "thruplays": "ThruPlays",
    "link_clicks": "Cliques no Link",
    "landing_page_views": "Visualizações de Página",
}

INSIGHT_FIELDS = ",".join([
    "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "frequency", "spend",
    "clicks", "unique_clicks", "ctr", "cpc", "cpm", "cpp",
    "actions", "action_values",
    "video_play_actions", "video_thruplay_watched_actions",
])

ADSET_FIELDS = ",".join([
    "adset_id", "adset_name", "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "frequency", "spend",
    "clicks", "unique_clicks", "ctr", "cpc", "cpm", "cpp",
    "actions", "action_values",
    "video_play_actions", "video_thruplay_watched_actions",
])

AD_FIELDS = ",".join([
    "ad_id", "ad_name", "adset_id", "adset_name", "campaign_id", "campaign_name", "objective",
    "impressions", "reach", "spend",
    "clicks", "ctr", "cpc", "cpm",
    "actions", "action_values",
])


def _get(url, params):
    params["access_token"] = ACCESS_TOKEN
    r = requests.get(url, params=params)
    data = r.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
    return data


def _paginate(response):
    results = response.get("data", [])
    data = response
    while "paging" in data and "next" in data.get("paging", {}):
        data = requests.get(data["paging"]["next"]).json()
        results.extend(data.get("data", []))
    return results


def _shift_months(d, months: int):
    import calendar
    m = d.month + months
    y = d.year + (m - 1) // 12
    m = ((m - 1) % 12) + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.replace(year=y, month=m, day=day)


def get_previous_period(since: str, until: str, mode: str = "previous") -> tuple:
    d_since = datetime.strptime(since, "%Y-%m-%d")
    d_until = datetime.strptime(until, "%Y-%m-%d")
    n_days = (d_until - d_since).days + 1
    if mode == "month":
        ps = _shift_months(d_since, -1)
        pu = _shift_months(d_until, -1)
    elif mode == "year":
        ps = d_since.replace(year=d_since.year - 1)
        pu = d_until.replace(year=d_until.year - 1)
    else:
        pu = d_since - timedelta(days=1)
        ps = pu - timedelta(days=n_days - 1)
    return str(ps.date()), str(pu.date())


@st.cache_data(ttl=3600, show_spinner=False)
def get_ad_accounts():
    data = _get(f"{BASE_URL}/me/adaccounts", {
        "fields": "id,name,account_status,currency,timezone_name",
        "limit": 100,
    })
    return _paginate(data)


@st.cache_data(ttl=3600, show_spinner=False)
def get_insights(account_id: str, since: str, until: str) -> pd.DataFrame:
    data = _get(f"{BASE_URL}/{account_id}/insights", {
        "fields": INSIGHT_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "campaign",
        "time_increment": 1,
        "limit": 500,
    })
    return _process(_paginate(data))


def get_insights_with_comparison(account_id: str, since: str, until: str,
                                  prev_since: str = None, prev_until: str = None):
    df_current = get_insights(account_id, since, until)
    if not prev_since or not prev_until:
        mode = st.session_state.get("_comp_mode", "previous")
        prev_since, prev_until = get_previous_period(since, until, mode)
    df_prev = get_insights(account_id, prev_since, prev_until)
    return df_current, df_prev, prev_since, prev_until


@st.cache_data(ttl=3600, show_spinner=False)
def get_adset_insights(account_id: str, since: str, until: str) -> pd.DataFrame:
    data = _get(f"{BASE_URL}/{account_id}/insights", {
        "fields": ADSET_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "adset",
        "time_increment": "all_days",
        "limit": 500,
    })
    return _process_adset(_paginate(data))


def get_adset_insights_with_comparison(account_id: str, since: str, until: str):
    df_current = get_adset_insights(account_id, since, until)
    mode = st.session_state.get("_comp_mode", "previous")
    prev_since, prev_until = get_previous_period(since, until, mode)
    df_prev = get_adset_insights(account_id, prev_since, prev_until)
    return df_current, df_prev, prev_since, prev_until


@st.cache_data(ttl=3600, show_spinner=False)
def get_ad_insights(account_id: str, since: str, until: str) -> pd.DataFrame:
    data = _get(f"{BASE_URL}/{account_id}/insights", {
        "fields": AD_FIELDS,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "ad",
        "time_increment": "all_days",
        "limit": 500,
    })
    return _process_ad(_paginate(data))


def _process(raw: list) -> pd.DataFrame:
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
            "date": r.get("date_start"),
            "campaign_id": r.get("campaign_id"),
            "campaign_name": r.get("campaign_name"),
            "objective": r.get("objective", ""),
            "campaign_type": OBJECTIVE_MAP.get(r.get("objective", ""), "other"),
            "impressions": int(r.get("impressions", 0)),
            "reach": int(r.get("reach", 0)),
            "frequency": float(r.get("frequency", 0)),
            "spend": spend,
            "clicks": int(r.get("clicks", 0)),
            "unique_clicks": int(r.get("unique_clicks", 0)),
            "ctr": float(r.get("ctr", 0)),
            "cpc": float(r.get("cpc") or 0),
            "cpm": float(r.get("cpm", 0)),
            "cpp": float(r.get("cpp") or 0),
            "link_clicks": actions.get("link_click", 0),
            "landing_page_views": actions.get("landing_page_view", 0),
            "post_engagement": actions.get("post_engagement", 0),
            "leads": leads,
            "purchases": purchases,
            "purchase_value": rev,
            "conversations": conversations,
            "roas": rev / spend if spend > 0 else 0,
            "cpl": spend / leads if leads > 0 else 0,
            "cpa": spend / purchases if purchases > 0 else 0,
            "cpc_conv": spend / conversations if conversations > 0 else 0,
            "video_plays": float(vp[0]["value"]) if vp else 0,
            "thruplays": float(tp[0]["value"]) if tp else 0,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _process_adset(raw: list) -> pd.DataFrame:
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


@st.cache_data(ttl=60, show_spinner=False)
def get_campaigns_management(account_id: str) -> list:
    data = _get(f"{BASE_URL}/{account_id}/campaigns", {
        "fields": "id,name,status,objective,daily_budget,lifetime_budget",
        "limit": 200,
    })
    raw = _paginate(data)
    return [c for c in raw if c.get("status") not in ("DELETED", "ARCHIVED")]


@st.cache_data(ttl=60, show_spinner=False)
def get_adsets_management(account_id: str) -> list:
    data = _get(f"{BASE_URL}/{account_id}/adsets", {
        "fields": "id,name,status,campaign_id,daily_budget,lifetime_budget",
        "limit": 500,
    })
    raw = _paginate(data)
    return [a for a in raw if a.get("status") not in ("DELETED", "ARCHIVED")]


@st.cache_data(ttl=60, show_spinner=False)
def get_ads_management(account_id: str) -> list:
    data = _get(f"{BASE_URL}/{account_id}/ads", {
        "fields": "id,name,status,adset_id,campaign_id",
        "limit": 1000,
    })
    raw = _paginate(data)
    return [a for a in raw if a.get("status") not in ("DELETED", "ARCHIVED")]


def update_status(object_id: str, status: str) -> dict:
    r = requests.post(f"{BASE_URL}/{object_id}", params={
        "access_token": ACCESS_TOKEN,
        "status": status,
    })
    data = r.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
    return data


def update_budget(object_id: str, daily_budget: float = None, lifetime_budget: float = None) -> dict:
    params = {"access_token": ACCESS_TOKEN}
    if daily_budget is not None:
        params["daily_budget"] = int(daily_budget * 100)
    if lifetime_budget is not None:
        params["lifetime_budget"] = int(lifetime_budget * 100)
    r = requests.post(f"{BASE_URL}/{object_id}", params=params)
    data = r.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
    return data


def _process_ad(raw: list) -> pd.DataFrame:
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
