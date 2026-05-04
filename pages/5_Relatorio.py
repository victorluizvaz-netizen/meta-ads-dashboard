import base64
import streamlit as st
from utils.meta_api import get_insights_with_comparison, get_adset_insights, get_ad_insights
from utils.report_generator import generate_report, generate_pdf_report
from utils.styles import css, section_header

st.set_page_config(page_title="Gerar Relatório | Meta Ads", page_icon="📄", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

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

    if not gerar:
        st.markdown("""
        <div style="background:white;border:1px solid #E4E6EB;border-radius:12px;padding:2rem;text-align:center;color:#65676B;">
            <p style="font-size:2.5rem;margin-bottom:0.5rem;">📊</p>
            <p style="font-weight:600;margin-bottom:0.5rem;">Relatório ainda não gerado</p>
            <p style="font-size:0.85rem;">Preencha os dados à esquerda e clique em <strong>Gerar Relatório</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
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

            # Busca dados de conjuntos e criativos quando necessário
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
                df=df,
                df_prev=df_prev,
                client_name=client_name.strip(),
                since=since,
                until=until,
                sections=sections,
                notes=notes,
                df_adsets=df_adsets,
                df_ads=df_ads,
            )

        st.success("✅ Relatório gerado com sucesso!")

        base_name = f"relatorio_{client_name.strip().lower().replace(' ', '_')}_{since}_{until}"

        col_html, col_pdf = st.columns(2)

        with col_html:
            b64_html = base64.b64encode(html.encode("utf-8")).decode()
            open_btn = f"""
            <script>
            function openReport() {{
                var b64 = '{b64_html}';
                var binary = atob(b64);
                var bytes = new Uint8Array(binary.length);
                for (var i = 0; i < binary.length; i++) {{ bytes[i] = binary.charCodeAt(i); }}
                var blob = new Blob([bytes], {{type: 'text/html; charset=utf-8'}});
                window.open(URL.createObjectURL(blob), '_blank');
            }}
            </script>
            <button onclick="openReport()" style="width:100%;padding:0.45rem 1rem;
                background:#6C63FF;color:white;border:none;border-radius:8px;
                font-weight:600;font-family:sans-serif;font-size:0.875rem;cursor:pointer;">
                🌐 Abrir relatório em nova aba
            </button>
            """
            st.components.v1.html(open_btn, height=48)
            st.caption("Só o relatório · Ctrl+P para salvar como PDF")

        with col_pdf:
            with st.spinner("Gerando PDF..."):
                try:
                    pdf_bytes = generate_pdf_report(
                        df=df, df_prev=df_prev,
                        client_name=client_name.strip(),
                        since=since, until=until,
                        sections=sections, notes=notes,
                        df_adsets=df_adsets,
                        df_ads=df_ads,
                    )
                    st.download_button(
                        label="⬇️ Baixar PDF",
                        data=pdf_bytes,
                        file_name=f"{base_name}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
                    st.caption("Abre em qualquer dispositivo")
                except ImportError as e:
                    if "pdf_unavailable" in str(e):
                        st.info("PDF não disponível nesta versão online. Baixe o HTML e abra no navegador para imprimir como PDF.")
                    else:
                        st.error(f"Erro ao gerar PDF: {e}")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

        st.divider()
        st.markdown("**Prévia do conteúdo incluído:**")
        for s in sections:
            type_map = {"Awareness": "awareness", "Tráfego": "traffic", "Leads": "leads", "Conversões": "conversions"}
            if s == "Visão Geral":
                count = df["campaign_name"].nunique()
                spend = df["spend"].sum()
                st.markdown(f"- **{s}** — {count} campanhas · R$ {spend:,.2f} investidos")
            elif s == "Alertas e Sugestões":
                from utils.alerts import generate_alerts
                n = len(generate_alerts(df, df_prev, df_adsets=df_adsets))
                st.markdown(f"- **{s}** — {n} alertas gerados")
            elif s == "Conjuntos de Anúncios":
                n_as = len(df_adsets) if df_adsets is not None and not df_adsets.empty else 0
                st.markdown(f"- **{s}** — {n_as} conjuntos incluídos")
            elif s == "Criativos":
                n_ads = len(df_ads) if df_ads is not None and not df_ads.empty else 0
                st.markdown(f"- **{s}** — {n_ads} anúncios incluídos")
            elif s in type_map:
                ct = type_map[s]
                dfs = df[df["campaign_type"] == ct]
                if not dfs.empty:
                    st.markdown(f"- **{s}** — {dfs['campaign_name'].nunique()} campanhas")
                else:
                    st.markdown(f"- **{s}** — *(sem dados no período)*")
