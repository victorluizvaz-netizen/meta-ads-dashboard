"""
Carrega/salva config_alertas.json.
Prioridade: arquivo local → GitHub Gist → st.secrets (fallback read-only).
"""
import json
import requests
import streamlit as st
from pathlib import Path

CONFIG_PATH    = Path(__file__).parent.parent / "config_alertas.json"
_GIST_FILENAME = "config_alertas.json"


def _gist_id() -> str:
    try:
        return st.secrets.get("GITHUB_GIST_ID", "")
    except Exception:
        return ""


def _gh_token() -> str:
    try:
        return st.secrets.get("GITHUB_TOKEN", "")
    except Exception:
        return ""


def _headers() -> dict:
    return {
        "Authorization": f"token {_gh_token()}",
        "Accept": "application/vnd.github+json",
    }


def load_config() -> dict:
    # 1. arquivo local (dev)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)

    # 2. GitHub Gist (Cloud com permissão de escrita)
    gist_id = _gist_id()
    if gist_id and _gh_token():
        try:
            r = requests.get(
                f"https://api.github.com/gists/{gist_id}",
                headers=_headers(),
                timeout=10,
            )
            if r.status_code == 200:
                content = r.json()["files"][_GIST_FILENAME]["content"]
                return json.loads(content)
        except Exception:
            pass

    # 3. st.secrets (fallback read-only)
    try:
        raw = st.secrets["config_alertas"]
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    # Local: escreve no arquivo
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return

    # Cloud: atualiza o Gist
    gist_id = _gist_id()
    if gist_id and _gh_token():
        requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers=_headers(),
            json={"files": {_GIST_FILENAME: {
                "content": json.dumps(cfg, ensure_ascii=False, indent=2)
            }}},
            timeout=10,
        )
        return

    # Fallback: cria o arquivo mesmo sem permissão (Streamlit Cloud aceita escrita temporária)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
