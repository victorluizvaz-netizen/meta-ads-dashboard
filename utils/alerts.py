import pandas as pd

FREQ_WARN      = 3.0
FREQ_CRITICAL  = 4.0
CTR_WARN_PCT   = 0.8
ROAS_CRITICAL  = 1.0
ROAS_WARN      = 2.0
ROAS_SCALE     = 3.0
CPL_INC_WARN   = 0.25
CPC_INC_WARN   = 0.25
CPM_INC_WARN   = 0.30
SPEND_NO_RESULT = 300.0


def _pct(cur, prv):
    if prv == 0:
        return None
    return (cur - prv) / prv


def _r(v):
    f = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {f}"


def generate_alerts(df: pd.DataFrame, df_prev: pd.DataFrame = None, df_adsets: pd.DataFrame = None) -> list:
    """
    Gera lista de alertas e sugestões baseados nos dados de campanhas e conjuntos.
    Cada item: {"level": "critical"|"warning"|"positive"|"info", "category": str, "title": str, "message": str}
    """
    alerts = []
    if df.empty:
        return alerts

    dp = df_prev if (df_prev is not None and not df_prev.empty) else None

    # ── Awareness: frequência ────────────────────────────────────────────────
    dfa = df[df["campaign_type"] == "awareness"]
    if not dfa.empty and dfa["reach"].sum() > 0:
        freq = dfa["impressions"].sum() / dfa["reach"].sum()
        if freq >= FREQ_CRITICAL:
            alerts.append({"level": "critical", "category": "Awareness",
                "title": "Frequência muito alta",
                "message": f"Frequência média de {freq:.1f}x nas campanhas de awareness. Público possivelmente saturado — expanda a segmentação ou pause temporariamente."})
        elif freq >= FREQ_WARN:
            alerts.append({"level": "warning", "category": "Awareness",
                "title": "Frequência elevada",
                "message": f"Frequência de {freq:.1f}x está acima de {FREQ_WARN:.0f}x. Monitore fadiga do público e considere rotacionar os criativos."})

    # ── Conversões: ROAS ────────────────────────────────────────────────────
    dfc = df[df["campaign_type"] == "conversions"]
    if not dfc.empty and dfc["spend"].sum() > 0:
        roas_v = dfc["purchase_value"].sum() / dfc["spend"].sum()
        if roas_v > 0:
            if roas_v < ROAS_CRITICAL:
                alerts.append({"level": "critical", "category": "Conversões",
                    "title": "ROAS abaixo de 1x",
                    "message": f"ROAS de {roas_v:.2f}x — o investimento não está sendo recuperado. Revise segmentação, criativos e página de destino urgentemente."})
            elif roas_v < ROAS_WARN:
                alerts.append({"level": "warning", "category": "Conversões",
                    "title": "ROAS abaixo de 2x",
                    "message": f"ROAS de {roas_v:.2f}x — positivo, mas há espaço para melhoria. Otimize anúncios com melhor CTR e menor CPA."})
            elif roas_v >= ROAS_SCALE:
                alerts.append({"level": "positive", "category": "Conversões",
                    "title": "Oportunidade de escala",
                    "message": f"ROAS de {roas_v:.2f}x indica excelente eficiência. Considere aumentar o orçamento para ampliar os resultados."})

    # ── Leads: CPL e volume ─────────────────────────────────────────────────
    dfl = df[df["campaign_type"] == "leads"]
    if not dfl.empty:
        total_l = dfl["leads"].sum()
        spend_l = dfl["spend"].sum()
        cpl_cur = spend_l / total_l if total_l > 0 else 0
        if dp is not None:
            dfl_p   = dp[dp["campaign_type"] == "leads"]
            prev_l  = dfl_p["leads"].sum() if not dfl_p.empty else 0
            prev_sl = dfl_p["spend"].sum() if not dfl_p.empty else 0
            cpl_prev = prev_sl / prev_l if prev_l > 0 else 0
            if cpl_cur > 0 and cpl_prev > 0:
                chg = _pct(cpl_cur, cpl_prev)
                if chg is not None and chg > CPL_INC_WARN:
                    alerts.append({"level": "warning", "category": "Leads",
                        "title": "Custo por Lead aumentou",
                        "message": f"CPL subiu {chg*100:.0f}% vs período anterior ({_r(cpl_prev)} → {_r(cpl_cur)}). Verifique qualidade do público e criativos de leads."})
                elif chg is not None and chg < -0.20:
                    alerts.append({"level": "positive", "category": "Leads",
                        "title": "CPL caindo — maior eficiência",
                        "message": f"Custo por Lead caiu {abs(chg)*100:.0f}% ({_r(cpl_prev)} → {_r(cpl_cur)}). Considere aumentar o orçamento para capturar mais leads."})
            if total_l > 0 and prev_l > 0:
                chg_l = _pct(total_l, prev_l)
                if chg_l is not None and chg_l > 0.20:
                    alerts.append({"level": "positive", "category": "Leads",
                        "title": "Volume de leads crescendo",
                        "message": f"Leads cresceram {chg_l*100:.0f}% vs período anterior ({int(prev_l)} → {int(total_l)}). Boa evolução — mantenha o investimento."})

    # ── Tráfego: CTR e CPC ──────────────────────────────────────────────────
    dft = df[df["campaign_type"] == "traffic"]
    if not dft.empty and dft["impressions"].sum() > 0:
        ctr_t = dft["clicks"].sum() / dft["impressions"].sum() * 100
        if 0 < ctr_t < CTR_WARN_PCT:
            alerts.append({"level": "warning", "category": "Tráfego",
                "title": "CTR baixo",
                "message": f"CTR médio de {ctr_t:.2f}% nas campanhas de tráfego está abaixo de {CTR_WARN_PCT}%. Teste novos criativos e CTAs mais claras."})
        if dp is not None:
            dft_p = dp[dp["campaign_type"] == "traffic"]
            if not dft_p.empty and dft_p["clicks"].sum() > 0 and dft["clicks"].sum() > 0:
                cpc_cur  = dft["spend"].sum() / dft["clicks"].sum()
                cpc_prev = dft_p["spend"].sum() / dft_p["clicks"].sum()
                chg_cpc  = _pct(cpc_cur, cpc_prev)
                if chg_cpc is not None and chg_cpc > CPC_INC_WARN:
                    alerts.append({"level": "warning", "category": "Tráfego",
                        "title": "CPC em alta",
                        "message": f"Custo por Clique subiu {chg_cpc*100:.0f}% vs período anterior ({_r(cpc_prev)} → {_r(cpc_cur)}). Pode indicar maior concorrência — revise lances e segmentação."})

    # ── CPM geral ───────────────────────────────────────────────────────────
    if dp is not None and not dp.empty and df["impressions"].sum() > 0 and dp["impressions"].sum() > 0:
        cpm_cur  = df["spend"].sum() / df["impressions"].sum() * 1000
        cpm_prev = dp["spend"].sum() / dp["impressions"].sum() * 1000
        chg_cpm  = _pct(cpm_cur, cpm_prev)
        if chg_cpm is not None and chg_cpm > CPM_INC_WARN:
            alerts.append({"level": "warning", "category": "Geral",
                "title": "CPM crescendo",
                "message": f"CPM subiu {chg_cpm*100:.0f}% ({_r(cpm_prev)} → {_r(cpm_cur)}). Sinal de maior concorrência no leilão ou saturação de público."})

    # ── Alto gasto sem resultado ─────────────────────────────────────────────
    camp_agg = df.groupby("campaign_name").agg(
        spend=("spend", "sum"), leads=("leads", "sum"),
        purchases=("purchases", "sum"), campaign_type=("campaign_type", "first"),
    ).reset_index()
    for _, row in camp_agg.iterrows():
        if (row["spend"] >= SPEND_NO_RESULT and row["leads"] == 0 and row["purchases"] == 0
                and row["campaign_type"] in ("leads", "conversions")):
            alerts.append({"level": "warning", "category": "Campanhas",
                "title": "Alto investimento sem conversões",
                "message": f"'{row['campaign_name'][:55]}' investiu {_r(row['spend'])} sem gerar leads ou compras. Revise público, criativo e página de destino."})

    # ── Nível de conjunto ────────────────────────────────────────────────────
    if df_adsets is not None and not df_adsets.empty:
        # Frequência crítica por conjunto (awareness)
        if "frequency" in df_adsets.columns:
            dfa_s = df_adsets[(df_adsets["campaign_type"] == "awareness") & (df_adsets["frequency"] >= FREQ_CRITICAL)]
            for _, row in dfa_s.iterrows():
                alerts.append({"level": "critical", "category": "Conjuntos",
                    "title": "Frequência crítica em conjunto",
                    "message": f"'{row['adset_name'][:55]}' com frequência de {row['frequency']:.1f}x. Pause ou expanda o público urgentemente."})

        # CTR muito baixo por conjunto (volume mínimo de 500 impressões)
        low_ctr = df_adsets[(df_adsets["ctr"] > 0) & (df_adsets["ctr"] < 0.5) & (df_adsets["impressions"] > 500)]
        for _, row in low_ctr.head(2).iterrows():
            alerts.append({"level": "warning", "category": "Conjuntos",
                "title": "CTR muito baixo",
                "message": f"'{row['adset_name'][:55]}' com CTR de {row['ctr']:.2f}%. Considere testar novos criativos ou revisar a segmentação."})

        # Melhor conjunto por ROAS — oportunidade de escala
        conv_s = df_adsets[(df_adsets["campaign_type"] == "conversions") & (df_adsets["roas"] >= ROAS_SCALE)]
        if not conv_s.empty:
            best = conv_s.sort_values("roas", ascending=False).iloc[0]
            alerts.append({"level": "positive", "category": "Conjuntos",
                "title": "Conjunto de alto desempenho",
                "message": f"'{best['adset_name'][:55]}' com ROAS de {best['roas']:.2f}x. Candidato ideal para aumento de orçamento."})

        # Melhor conjunto por CPL — oportunidade de escala
        leads_s = df_adsets[(df_adsets["campaign_type"] == "leads") & (df_adsets["cpl"] > 0)]
        if len(leads_s) >= 2:
            avg_cpl = leads_s["cpl"].mean()
            best_l  = leads_s.sort_values("cpl").iloc[0]
            if best_l["cpl"] < avg_cpl * 0.70:
                alerts.append({"level": "positive", "category": "Conjuntos",
                    "title": "Conjunto com CPL abaixo da média",
                    "message": f"'{best_l['adset_name'][:55]}' com CPL de {_r(best_l['cpl'])} vs média de {_r(avg_cpl)}. Considere aumentar o orçamento deste conjunto."})

    return alerts
