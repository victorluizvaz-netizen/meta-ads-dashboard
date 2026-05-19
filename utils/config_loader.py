"""
Carrega config_alertas.json — arquivo local em dev, st.secrets na Cloud.
"""
import json
import streamlit as st
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config_alertas.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    try:
        raw = st.secrets["config_alertas"]
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except Exception:
        return {}


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
