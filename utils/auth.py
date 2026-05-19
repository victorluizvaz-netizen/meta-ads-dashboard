import streamlit as st
from utils.config_loader import load_config


def require_login() -> None:
    if st.session_state.get("_is_client"):
        return
    if st.session_state.get("_authenticated"):
        return

    cfg = load_config()
    password = cfg.get("dashboard_password", "")
    if not password:
        try:
            password = st.secrets.get("dashboard_password", "")
        except Exception:
            password = ""

    if not password:
        st.session_state["_authenticated"] = True
        return

    st.markdown(
        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'min-height:70vh;gap:1.2rem;">'
        '<div style="font-size:3rem;">🔐</div>'
        '<h2 style="color:#F1ECF8;margin:0;">Meta Ads Dashboard</h2>'
        '<p style="color:#8B7EAF;margin:0 0 0.5rem;">Digite a senha para continuar.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        pwd = st.text_input("Senha", type="password", key="_login_pwd", label_visibility="collapsed",
                            placeholder="Senha de acesso")
        if st.button("Entrar", type="primary", use_container_width=True, key="_login_btn"):
            if pwd == password:
                st.session_state["_authenticated"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    st.stop()
