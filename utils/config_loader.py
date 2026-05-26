"""
Carrega/salva config_alertas.json.
Prioridade de leitura: arquivo local → GitHub Gist → st.secrets.
Salvamento: arquivo local E GitHub Gist (quando credenciais disponíveis).
"""
import json
import requests
from pathlib import Path

CONFIG_PATH    = Path(__file__).parent.parent / "config_alertas.json"
_GIST_FILENAME = "config_alertas.json"


def _gist_id(cfg: dict | None = None) -> str:
    if cfg and cfg.get("github_gist_id"):
        return cfg["github_gist_id"]
    try:
        import streamlit as st
        return st.secrets.get("GITHUB_GIST_ID", "")
    except Exception:
        return ""


def _gh_token(cfg: dict | None = None) -> str:
    if cfg and cfg.get("github_token"):
        return cfg["github_token"]
    try:
        import streamlit as st
        return st.secrets.get("GITHUB_TOKEN", "")
    except Exception:
        return ""


def _gist_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }


def _fetch_gist(gist_id: str, token: str) -> dict | None:
    """Busca config do Gist. Não depende de streamlit."""
    if not (gist_id and token):
        return None
    try:
        r = requests.get(
            f"https://api.github.com/gists/{gist_id}",
            headers=_gist_headers(token),
            timeout=10,
        )
        if r.status_code == 200:
            content = r.json()["files"].get(_GIST_FILENAME, {}).get("content")
            if content:
                return json.loads(content)
    except Exception:
        pass
    return None


def _push_gist(cfg: dict, gist_id: str, token: str) -> bool:
    """Publica config no Gist, removendo github_token antes de publicar."""
    if not (gist_id and token):
        return False
    safe_cfg = {k: v for k, v in cfg.items() if k != "github_token"}
    try:
        r = requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers=_gist_headers(token),
            json={"files": {_GIST_FILENAME: {
                "content": json.dumps(safe_cfg, ensure_ascii=False, indent=2)
            }}},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def load_config() -> dict:
    # 1. arquivo local
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)

    # 2. GitHub Gist
    remote = _fetch_gist(_gist_id(), _gh_token())
    if remote:
        return remote

    # 3. st.secrets (fallback read-only)
    try:
        import streamlit as st
        raw = st.secrets["config_alertas"]
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except Exception:
        return {}


def sync_from_gist(local_cfg: dict) -> dict:
    """
    Sincroniza config com Gist sem depender de streamlit (uso no runner).
    Usa credenciais do próprio config local.
    Preserva github_token local no resultado (não fica no Gist).
    """
    gist_id = local_cfg.get("github_gist_id", "")
    token   = local_cfg.get("github_token", "")
    remote  = _fetch_gist(gist_id, token)
    if remote:
        remote["github_gist_id"] = gist_id
        remote["github_token"]   = token
        import os
        new_token = remote.get("meta_access_token", "")
        if new_token and new_token != "SEU_TOKEN_META_AQUI":
            os.environ["META_ACCESS_TOKEN"] = new_token
        return remote
    return local_cfg


def save_config(cfg: dict) -> None:
    """Salva config localmente E sincroniza com Gist."""
    gist_id = _gist_id(cfg)
    token   = _gh_token(cfg)

    # Salva localmente
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        # Sincroniza com Gist se credenciais disponíveis no config
        if gist_id and token:
            _push_gist(cfg, gist_id, token)
        return

    # Cloud: salva no Gist
    if gist_id and token:
        _push_gist(cfg, gist_id, token)
        return

    # Último recurso: cria o arquivo
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
