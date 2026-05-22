import streamlit as st

OPT_GOAL_PT = {
    "REACH": "Alcance", "LINK_CLICKS": "Cliques no Link", "IMPRESSIONS": "Impressões",
    "LEAD_GENERATION": "Geração de Leads", "OFFSITE_CONVERSIONS": "Conversões",
    "LANDING_PAGE_VIEWS": "Visualizações de Página", "THRUPLAY": "ThruPlay",
    "APP_INSTALLS": "Instalações de App", "POST_ENGAGEMENT": "Engajamento",
    "CONVERSATIONS": "Conversas", "QUALITY_LEAD": "Leads de Qualidade",
    "REPLIES": "Respostas", "QUALITY_CALL": "Chamadas de Qualidade",
    "PAGE_LIKES": "Curtidas na Página",
}
BILLING_PT = {
    "IMPRESSIONS": "Por Impressões (CPM)", "LINK_CLICKS": "Por Cliques (CPC)",
    "THRUPLAY": "Por ThruPlay", "APP_INSTALLS": "Por Instalações", "PAGE_LIKES": "Por Curtidas",
}
BID_STRAT_PT = {
    "LOWEST_COST_WITHOUT_CAP": "Menor Custo (automático)",
    "LOWEST_COST_WITH_BID_CAP": "Lance Máximo",
    "COST_CAP": "Meta de Custo",
    "MINIMUM_ROAS": "ROAS Mínimo",
}
DEST_TYPE_PT = {
    "WEBSITE": "Site", "APP": "Aplicativo", "MESSENGER": "Messenger",
    "INSTAGRAM_DIRECT": "Direct Instagram", "FACEBOOK": "Facebook",
    "WHATSAPP": "WhatsApp", "ON_AD": "No Anúncio", "SHOP_AUTOMATIC": "Loja (automático)",
}
PLATFORM_PT = {
    "facebook": "Facebook", "instagram": "Instagram",
    "audience_network": "Audience Network", "messenger": "Messenger",
}
FB_POS_PT = {
    "feed": "Feed", "story": "Stories", "video_feeds": "Feeds de Vídeo",
    "marketplace": "Marketplace", "search": "Pesquisa",
    "instant_article": "Artigos Instantâneos", "right_hand_column": "Coluna Direita",
    "instream_video": "Vídeo In-Stream", "reels": "Reels",
}
IG_POS_PT = {
    "stream": "Feed", "story": "Stories", "reels": "Reels",
    "explore": "Explorar", "explore_home": "Pág. Inicial Explorar",
    "instagram_profile_reels": "Reels do Perfil", "ig_search": "Pesquisa",
}
COUNTRY_PT = {
    "BR": "Brasil", "US": "Estados Unidos", "AR": "Argentina",
    "CL": "Chile", "CO": "Colômbia", "MX": "México", "PT": "Portugal", "ES": "Espanha",
}
LOCALE_PT = {
    6: "Português (BR)", 5: "Inglês (EUA)", 23: "Espanhol",
    7: "Francês", 8: "Alemão", 9: "Italiano", 46: "Português (PT)",
}


def render_adset_config(cfg: dict) -> None:
    """Renderiza a configuração completa de um conjunto de anúncios via Streamlit."""
    if "error" in cfg:
        st.error(f"Erro ao carregar configuração: {cfg['error'].get('message', 'desconhecido')}")
        return

    targeting = cfg.get("targeting") or {}

    # ── Otimização e entrega ──────────────────────────────────────────────────
    st.markdown("#### ⚙️ Otimização e Entrega")
    c1, c2, c3 = st.columns(3)

    opt_goal = cfg.get("optimization_goal", "")
    c1.markdown(f"**Objetivo de Otimização**\n\n{OPT_GOAL_PT.get(opt_goal, opt_goal or '—')}")

    billing = cfg.get("billing_event", "")
    c2.markdown(f"**Evento de Cobrança**\n\n{BILLING_PT.get(billing, billing or '—')}")

    bid_strat = cfg.get("bid_strategy", "")
    bid_amt   = cfg.get("bid_amount")
    bid_label = BID_STRAT_PT.get(bid_strat, bid_strat or "—")
    if bid_amt:
        bid_label += f" · R$ {int(bid_amt) / 100:.2f}"
    c3.markdown(f"**Estratégia de Lance**\n\n{bid_label}")

    c4, c5, c6 = st.columns(3)
    dest = cfg.get("destination_type", "")
    c4.markdown(f"**Destino**\n\n{DEST_TYPE_PT.get(dest, dest or '—')}")

    start = (cfg.get("start_time") or "")[:10] or "—"
    end   = (cfg.get("end_time")   or "")[:10] or "Sem data fim"
    c5.markdown(f"**Início**\n\n{start}")
    c6.markdown(f"**Término**\n\n{end}")

    st.divider()

    # ── Público-alvo ──────────────────────────────────────────────────────────
    st.markdown("#### 👥 Público-Alvo")
    col_demo, col_aud = st.columns(2)

    with col_demo:
        st.markdown("**Dados Demográficos e Localização**")

        age_min = targeting.get("age_min", 18)
        age_max = targeting.get("age_max", 65)
        st.markdown(f"🎂 **Idade:** {age_min} – {age_max} anos")

        genders = targeting.get("genders", [])
        if not genders or set(genders) >= {1, 2}:
            gender_label = "Todos"
        elif 1 in genders:
            gender_label = "Masculino"
        else:
            gender_label = "Feminino"
        st.markdown(f"👤 **Gênero:** {gender_label}")

        locales = targeting.get("locales", [])
        if locales:
            locale_names = [LOCALE_PT.get(lo, str(lo)) for lo in locales]
            st.markdown(f"🗣️ **Idioma:** {', '.join(locale_names)}")

        geo = targeting.get("geo_locations", {})
        loc_lines = []
        for code in geo.get("countries", []):
            loc_lines.append(COUNTRY_PT.get(code, code))
        for city in geo.get("cities", []):
            loc_lines.append(f"{city.get('name', '')} ({city.get('country', '')})")
        for region in geo.get("regions", []):
            loc_lines.append(region.get("name", ""))
        if loc_lines:
            st.markdown("📌 **Localização:** " + " · ".join(loc_lines))

    with col_aud:
        st.markdown("**Públicos Personalizados**")
        custom_aud = targeting.get("custom_audiences", [])
        excl_aud   = targeting.get("excluded_custom_audiences", [])
        if custom_aud:
            st.markdown(f"✅ **Incluídos ({len(custom_aud)}):**")
            for ca in custom_aud:
                st.markdown(f"- {ca.get('name', ca.get('id', '?'))}")
        if excl_aud:
            st.markdown(f"🚫 **Excluídos ({len(excl_aud)}):**")
            for ea in excl_aud:
                st.markdown(f"- {ea.get('name', ea.get('id', '?'))}")
        if not custom_aud and not excl_aud:
            st.markdown("_Nenhum público personalizado configurado_")

    # ── Interesses e comportamentos ───────────────────────────────────────────
    flex = targeting.get("flexible_spec", [])
    all_interests = list(targeting.get("interests", []))
    all_behaviors = list(targeting.get("behaviors", []))
    for group in flex:
        all_interests.extend(group.get("interests", []))
        all_behaviors.extend(group.get("behaviors", []))

    if all_interests or all_behaviors:
        st.divider()
        st.markdown("#### 🎯 Interesses e Comportamentos")
        ci, cb = st.columns(2)
        with ci:
            if all_interests:
                st.markdown(f"**Interesses ({len(all_interests)}):**")
                for item in all_interests:
                    st.markdown(f"- {item.get('name', '?')}")
        with cb:
            if all_behaviors:
                st.markdown(f"**Comportamentos ({len(all_behaviors)}):**")
                for item in all_behaviors:
                    st.markdown(f"- {item.get('name', '?')}")

    st.divider()

    # ── Posicionamentos ───────────────────────────────────────────────────────
    st.markdown("#### 📱 Posicionamentos")
    platforms = targeting.get("publisher_platforms", [])
    fb_pos    = targeting.get("facebook_positions", [])
    ig_pos    = targeting.get("instagram_positions", [])
    devices   = targeting.get("device_platforms", [])

    if not platforms:
        st.markdown("_Posicionamentos automáticos (Advantage+)_")
    else:
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown("**Plataformas:**")
            for p in platforms:
                st.markdown(f"- {PLATFORM_PT.get(p, p)}")
        with p2:
            if fb_pos:
                st.markdown("**Facebook:**")
                for pos in fb_pos:
                    st.markdown(f"- {FB_POS_PT.get(pos, pos)}")
        with p3:
            if ig_pos:
                st.markdown("**Instagram:**")
                for pos in ig_pos:
                    st.markdown(f"- {IG_POS_PT.get(pos, pos)}")
        with p4:
            st.markdown("**Dispositivos:**")
            if devices:
                for d in devices:
                    st.markdown(f"- {'Mobile' if d == 'mobile' else 'Desktop' if d == 'desktop' else d}")
            else:
                st.markdown("- Todos")
