"""
Guard de acesso para clientes externos.

Uso: chamar redirect_if_client() logo após st.markdown(css(), ...) em cada página.
Cliente.py define _is_client e _client_token na session_state após validar o token.
"""
import streamlit as st
import streamlit.components.v1 as components


def redirect_if_client() -> None:
    """
    Se o visitante for um cliente (sessão iniciada via Cliente.py),
    redireciona imediatamente de volta ao painel dele via JS.
    Bloqueia acesso a qualquer outra página do dashboard.
    """
    if not st.session_state.get("_is_client"):
        return
    token = st.session_state.get("_client_token", "")
    if not token:
        return

    # window.top garante que o redirect afeta a aba inteira, não só o iframe do componente
    components.html(
        f'<script>window.top.location.href = "/Cliente?token={token}";</script>',
        height=0,
    )
    # Fallback textual caso JS seja bloqueado pelo browser
    st.info("↩️ Esta página não está disponível para o seu perfil de acesso.")
    st.markdown(f"[← Voltar ao seu painel](/Cliente?token={token})")
    st.stop()
