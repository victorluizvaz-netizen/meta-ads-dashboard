def currency(value: float, symbol: str = "R$") -> str:
    if value == 0:
        return f"{symbol} 0,00"
    f = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{symbol} {f}"


def number(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{int(value):,}".replace(",", ".")


def percent(value: float) -> str:
    return f"{value:.2f}%"


def roas(value: float) -> str:
    return f"{value:.2f}x"


def delta_pct(current: float, previous: float) -> tuple:
    """Returns (delta_string, is_positive)"""
    if previous == 0:
        return None, None
    pct = (current - previous) / previous * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%", pct >= 0


def insight_text(metric_label: str, current: float, previous: float, lower_is_better: bool = False) -> str:
    if previous == 0:
        return f"{metric_label} sem dado do período anterior para comparação."
    pct = (current - previous) / previous * 100
    direction = "cresceu" if pct > 0 else "caiu"
    good = (pct > 0 and not lower_is_better) or (pct < 0 and lower_is_better)
    qualifier = "uma boa notícia" if good else "atenção necessária"
    return f"{metric_label} {direction} {abs(pct):.0f}% vs o período anterior — {qualifier}."


def top_insight(df_current, df_prev, campaign_type: str = None) -> str:
    import pandas as pd
    if df_current.empty:
        return "Sem dados no período selecionado."
    if campaign_type:
        df_c = df_current[df_current["campaign_type"] == campaign_type]
        df_p = df_prev[df_prev["campaign_type"] == campaign_type] if not df_prev.empty else pd.DataFrame()
    else:
        df_c, df_p = df_current, df_prev

    if df_c.empty:
        return "Nenhuma campanha deste tipo no período."

    metrics = [
        ("spend", "O investimento", False),
        ("impressions", "As impressões", False),
        ("leads", "Os leads", False),
        ("purchases", "As compras", False),
        ("roas", "O ROAS", False),
        ("cpl", "O custo por lead", True),
        ("cpa", "O custo por aquisição", True),
        ("cpc", "O custo por clique", True),
    ]

    best_text, best_pct = "", 0
    for col, label, lower_is_better in metrics:
        if col not in df_c.columns:
            continue
        cur = df_c[col].sum() if col not in ("roas", "cpl", "cpa", "cpc", "frequency") else df_c[col].mean()
        prv = df_p[col].sum() if (not df_p.empty and col in df_p.columns and col not in ("roas", "cpl", "cpa", "cpc", "frequency")) else (df_p[col].mean() if (not df_p.empty and col in df_p.columns) else 0)
        if prv == 0 or cur == 0:
            continue
        pct = abs((cur - prv) / prv * 100)
        if pct > best_pct:
            best_pct = pct
            best_text = insight_text(label, cur, prv, lower_is_better)

    return best_text if best_text else "Dados carregados. Selecione um período com histórico para ver comparativos."
