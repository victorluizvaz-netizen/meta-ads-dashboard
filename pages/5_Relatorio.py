import base64
import urllib.parse
import streamlit as st
import streamlit.components.v1 as stv1
from utils.meta_api import get_insights_with_comparison, get_adset_insights, get_ad_insights
from utils.report_generator import generate_report, generate_pdf_report
from utils.config_loader import load_config
from utils.styles import css, section_header

st.set_page_config(page_title="Gerar Relatório | Meta Ads", page_icon="📄", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

from utils.client_guard import redirect_if_client
redirect_if_client()

account_id = st.session_state.get("account_id")
since = st.session_state.get("since")
until = st.session_state.get("until")

if not account_id:
    st.warning("⚠️ Volte à página principal e selecione uma conta antes de gerar o relatório.")
    st.stop()

st.title("📄 Gerar Relatório do Cliente")
st.caption("Configure o relatório abaixo e clique em Gerar. O arquivo HTML pode ser enviado por email ou compartilhado pelo Drive.")
st.divider()

col_form, col_preview = st.columns([1, 1.6], gap="large")

with col_form:
    st.markdown(section_header("Dados do cliente"), unsafe_allow_html=True)
    client_name = st.text_input("Nome do cliente", placeholder="Ex: Faciallis Estética")
    notes = st.text_area("Observações / contexto (opcional)", placeholder="Ex: Período de lançamento de nova campanha. Investimento aumentado em 30% em relação ao mês anterior.", height=100)

    st.markdown(section_header("Seções do relatório"), unsafe_allow_html=True)
    sections = st.multiselect(
        "Incluir seções",
        ["Alertas e Sugestões", "Visão Geral", "Awareness", "Tráfego", "Leads", "Conversões", "Conjuntos de Anúncios", "Criativos"],
        default=["Alertas e Sugestões", "Visão Geral", "Awareness", "Tráfego", "Leads", "Conversões", "Conjuntos de Anúncios", "Criativos"],
    )

    st.markdown(section_header("Período"), unsafe_allow_html=True)
    st.info(f"📅 Período selecionado: **{since}** → **{until}**\n\nPara alterar, volte à página principal.")

    st.divider()
    gerar = st.button("⚡ Gerar Relatório", type="primary", use_container_width=True)

with col_preview:
    st.markdown(section_header("Prévia do relatório", "O relatório será gerado com os dados do período selecionado."), unsafe_allow_html=True)

    # ── Geração (só quando botão clicado) ────────────────────────────────────
    if gerar:
        if not client_name.strip():
            st.error("Preencha o nome do cliente antes de gerar.")
            st.stop()
        if not sections:
            st.error("Selecione ao menos uma seção.")
            st.stop()

        with st.spinner("Buscando dados e gerando relatório..."):
            try:
                df, df_prev, prev_since, prev_until = get_insights_with_comparison(account_id, since, until)
            except Exception as e:
                st.error(f"Erro ao buscar dados: {e}")
                st.stop()

            selected = st.session_state.get("selected_campaigns", [])
            if selected:
                df = df[df["campaign_name"].isin(selected)]
                if not df_prev.empty:
                    df_prev = df_prev[df_prev["campaign_name"].isin(selected)]

            if df.empty:
                st.warning("Nenhum dado encontrado para o período selecionado.")
                st.stop()

            df_adsets = None
            needs_adsets = any(s in sections for s in ("Alertas e Sugestões", "Conjuntos de Anúncios"))
            if needs_adsets:
                try:
                    df_adsets = get_adset_insights(account_id, since, until)
                    if selected and df_adsets is not None and not df_adsets.empty:
                        df_adsets = df_adsets[df_adsets["campaign_name"].isin(selected)]
                except Exception:
                    df_adsets = None

            df_ads = None
            if "Criativos" in sections:
                try:
                    df_ads = get_ad_insights(account_id, since, until)
                    if selected and df_ads is not None and not df_ads.empty:
                        df_ads = df_ads[df_ads["campaign_name"].isin(selected)]
                except Exception:
                    df_ads = None

            html = generate_report(
                df=df, df_prev=df_prev, client_name=client_name.strip(),
                since=since, until=until, sections=sections, notes=notes,
                df_adsets=df_adsets, df_ads=df_ads,
            )

            pdf_bytes = None
            try:
                pdf_bytes = generate_pdf_report(
                    df=df, df_prev=df_prev, client_name=client_name.strip(),
                    since=since, until=until, sections=sections, notes=notes,
                    df_adsets=df_adsets, df_ads=df_ads,
                )
            except Exception:
                pass

        # Preview stats (sem guardar DataFrames inteiros)
        _preview = {}
        for s in sections:
            if s == "Visão Geral":
                _preview[s] = f"{df['campaign_name'].nunique()} campanhas · R$ {df['spend'].sum():,.2f} investidos"
            elif s == "Alertas e Sugestões":
                from utils.alerts import generate_alerts
                _preview[s] = f"{len(generate_alerts(df, df_prev, df_adsets=df_adsets))} alertas gerados"
            elif s == "Conjuntos de Anúncios":
                n_as = len(df_adsets) if df_adsets is not None and not df_adsets.empty else 0
                _preview[s] = f"{n_as} conjuntos incluídos"
            elif s == "Criativos":
                n_ads = len(df_ads) if df_ads is not None and not df_ads.empty else 0
                _preview[s] = f"{n_ads} anúncios incluídos"
            else:
                type_map = {"Awareness": "awareness", "Tráfego": "traffic", "Leads": "leads", "Conversões": "conversions"}
                ct  = type_map.get(s)
                dfs = df[df["campaign_type"] == ct] if ct else None
                _preview[s] = f"{dfs['campaign_name'].nunique()} campanhas" if (dfs is not None and not dfs.empty) else "*(sem dados no período)*"

        # Salva no session_state para sobreviver a reruns
        st.session_state["_rpt_cache"] = {
            "html":        html,
            "pdf_bytes":   pdf_bytes,
            "base_name":   f"relatorio_{client_name.strip().lower().replace(' ', '_')}_{since}_{until}",
            "client_name": client_name.strip(),
            "since":       since,
            "until":       until,
            "account_id":  account_id,
            "preview":     _preview,
        }

    # ── Exibição (persiste nos reruns) ────────────────────────────────────────
    _rpt = st.session_state.get("_rpt_cache")

    if not _rpt:
        st.markdown("""
        <div style="background:rgba(19,14,39,0.8);border:1px solid rgba(168,85,247,0.15);border-radius:12px;
        padding:2rem;text-align:center;color:#8B7EAF;">
            <p style="font-size:2.5rem;margin-bottom:0.5rem;">📊</p>
            <p style="font-weight:600;margin-bottom:0.5rem;color:#F1ECF8;">Relatório ainda não gerado</p>
            <p style="font-size:0.85rem;">Preencha os dados à esquerda e clique em <strong>Gerar Relatório</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        html      = _rpt["html"]
        pdf_bytes = _rpt["pdf_bytes"]
        base_name = _rpt["base_name"]

        st.success("✅ Relatório gerado com sucesso!")

        b64_html = base64.b64encode(html.encode("utf-8")).decode()
        stv1.html(f"""
        <style>
          a.btn{{display:block;width:100%;padding:0.6rem 1rem;background:#6C63FF;
          color:white;border-radius:8px;font-weight:600;font-size:0.95rem;
          font-family:sans-serif;text-align:center;text-decoration:none;cursor:pointer;
          box-sizing:border-box;}}
          a.btn:hover{{background:#5b52e6;}}
        </style>
        <a id="rpt" class="btn" href="#" target="_blank">🌐 Abrir relatório em nova aba</a>
        <script>
        (function(){{
          try{{
            var b64="{b64_html}";
            var bin=atob(b64);
            var u=new Uint8Array(bin.length);
            for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
            var blob=new Blob([u],{{type:'text/html;charset=utf-8'}});
            document.getElementById('rpt').href=URL.createObjectURL(blob);
          }}catch(e){{
            var el=document.getElementById('rpt');
            el.textContent='⚠️ Erro: '+e.message;
            el.style.background='#dc3545';
          }}
        }})();
        </script>
        """, height=55)
        st.caption("Só o relatório é aberto · use Ctrl+P para salvar como PDF")

        col_html, col_pdf = st.columns(2)
        with col_html:
            st.download_button(
                label="⬇️ Baixar HTML",
                data=html.encode("utf-8"),
                file_name=f"{base_name}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.caption("Alternativa: salvar arquivo")
        with col_pdf:
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"{base_name}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
                st.caption("Abre em qualquer dispositivo")
            else:
                st.info("PDF não disponível nesta versão online. Use Ctrl+P no relatório HTML.")

        # ── Compartilhar painel no WhatsApp ──────────────────────────────────
        _cfg = load_config()
        _acct_conf = next((c for c in _cfg.get("contas", []) if c["account_id"] == _rpt["account_id"]), None)
        if _acct_conf:
            _public_url   = _cfg.get("public_url", "").rstrip("/")
            _client_token = _acct_conf.get("client_token", "")
            if _public_url and _client_token:
                _link = f"{_public_url}/Cliente?token={_client_token}"
                _msg  = f"📊 *Relatório Meta Ads — {_rpt['client_name']}*\n📅 {_rpt['since']} a {_rpt['until']}\n\n👉 {_link}"

                _whatsapps = _acct_conf.get("whatsapps") or ([_acct_conf["whatsapp"]] if _acct_conf.get("whatsapp") else [])
                _options   = [f"+{n}" for n in _whatsapps] + ["Outro número..."]

                st.markdown("**📲 Enviar painel no WhatsApp**")
                _col_sel, _col_inp = st.columns([2, 2])
                with _col_sel:
                    _sel = st.selectbox("Destinatário", _options, key="wa_dest_sel", label_visibility="collapsed")
                with _col_inp:
                    _custom = ""
                    if _sel == "Outro número...":
                        _custom = st.text_input("Número", placeholder="5549999999999",
                                                key="wa_dest_custom", label_visibility="collapsed")

                _num = _custom.strip().replace("+", "").replace(" ", "").replace("-", "") if _sel == "Outro número..." else _sel.replace("+", "")
                if _num:
                    _wa = f"https://wa.me/{_num}?text={urllib.parse.quote(_msg)}"
                    st.markdown(
                        f'<a href="{_wa}" target="_blank" style="display:inline-flex;align-items:center;gap:0.5rem;'
                        f'background:rgba(37,211,102,0.12);border:1px solid rgba(37,211,102,0.3);color:#4ADE80;'
                        f'border-radius:8px;padding:0.5rem 1rem;font-weight:600;text-decoration:none;font-size:0.9rem;">'
                        f'📲 Abrir WhatsApp</a>',
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.markdown("**Prévia do conteúdo incluído:**")
        for s, desc in _rpt.get("preview", {}).items():
            st.markdown(f"- **{s}** — {desc}")
