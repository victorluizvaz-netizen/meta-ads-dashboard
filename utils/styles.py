def css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* ── Layout ───────────────────────────────────────────────── */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
        }

        /* ── Scrollbar ────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: rgba(74, 222, 128, 0.22);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: rgba(74, 222, 128, 0.42); }

        /* ── Typography ───────────────────────────────────────────── */
        h1 {
            font-size: 1.7rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em !important;
            color: #ECFDF5 !important;
        }

        /* ── Sidebar ──────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: #080A08 !important;
            border-right: 1px solid rgba(74, 222, 128, 0.07) !important;
        }
        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        .stSidebar .stCaption { color: #3A5A3A !important; }
        .stSidebar label { color: #5A7A5A !important; }

        /* ── Metric cards ─────────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: linear-gradient(160deg, #121A12 0%, #0E140E 100%);
            border: 1px solid rgba(74, 222, 128, 0.09);
            border-top: 1px solid rgba(74, 222, 128, 0.18);
            border-radius: 16px;
            padding: 1.2rem 1.4rem 1.1rem;
            box-shadow:
                0 4px 24px rgba(0,0,0,0.55),
                inset 0 1px 0 rgba(255,255,255,0.025);
            transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
        }
        div[data-testid="metric-container"]:hover {
            border-color: rgba(74, 222, 128, 0.28);
            border-top-color: rgba(74, 222, 128, 0.5);
            box-shadow:
                0 8px 32px rgba(0,0,0,0.65),
                0 0 22px rgba(74, 222, 128, 0.06),
                inset 0 1px 0 rgba(255,255,255,0.04);
            transform: translateY(-2px);
        }
        div[data-testid="metric-container"] label {
            color: #3E5E3E !important;
            font-size: 0.70rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.09em;
        }
        div[data-testid="stMetricValue"] > div {
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            color: #ECFDF5 !important;
            letter-spacing: -0.025em !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stMetricDelta"] {
            font-size: 0.76rem !important;
            font-weight: 500 !important;
            opacity: 0.85;
        }

        /* ── Chart panels ─────────────────────────────────────────── */
        div[data-testid="stPlotlyChart"] {
            background: linear-gradient(160deg, #111811 0%, #0E140E 100%);
            border: 1px solid rgba(74, 222, 128, 0.08);
            border-top: 1px solid rgba(74, 222, 128, 0.13);
            border-radius: 16px;
            padding: 0.4rem 0.2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.45);
            transition: border-color 0.2s ease;
        }
        div[data-testid="stPlotlyChart"]:hover {
            border-color: rgba(74, 222, 128, 0.16);
        }

        /* ── Dividers ─────────────────────────────────────────────── */
        hr {
            border: none !important;
            border-top: 1px solid rgba(74, 222, 128, 0.06) !important;
            margin: 1.5rem 0 !important;
        }

        /* ── Expander ─────────────────────────────────────────────── */
        details {
            background: linear-gradient(160deg, #111811 0%, #0E140E 100%) !important;
            border: 1px solid rgba(74, 222, 128, 0.08) !important;
            border-radius: 14px !important;
        }
        details[open] { border-color: rgba(74, 222, 128, 0.15) !important; }
        details summary {
            color: #5A7A5A !important;
            font-size: 0.87rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 0 !important;
        }

        /* ── Dataframe ────────────────────────────────────────────── */
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(74, 222, 128, 0.08) !important;
            border-radius: 12px !important;
            overflow: hidden;
        }

        /* ── Spinner ──────────────────────────────────────────────── */
        .stSpinner > div { border-top-color: #4ADE80 !important; }

        /* ── Input fields ─────────────────────────────────────────── */
        div[data-baseweb="select"] > div {
            background: #0E150E !important;
            border-color: rgba(74, 222, 128, 0.14) !important;
            border-radius: 10px !important;
        }
        div[data-baseweb="input"] > div {
            background: #0E150E !important;
            border-color: rgba(74, 222, 128, 0.14) !important;
            border-radius: 10px !important;
        }

        /* ── Multiselect tag ──────────────────────────────────────── */
        span[data-baseweb="tag"] {
            background: rgba(74, 222, 128, 0.12) !important;
            border: 1px solid rgba(74, 222, 128, 0.25) !important;
            border-radius: 6px !important;
            color: #86EFAC !important;
        }

        /* ── Date input ───────────────────────────────────────────── */
        div[data-testid="stDateInput"] input {
            background: #0E150E !important;
            border-color: rgba(74, 222, 128, 0.14) !important;
            border-radius: 10px !important;
        }

        /* ── Alert boxes ──────────────────────────────────────────── */
        div[data-testid="stAlert"] {
            border-radius: 12px !important;
        }
    </style>
    """


def insight_box(text: str, icon: str = "💡"):
    return f"""
    <div style="
        background: linear-gradient(135deg, rgba(6,78,59,0.55) 0%, rgba(6,95,70,0.35) 100%);
        color: #A7F3D0;
        padding: 0.95rem 1.4rem;
        border-radius: 14px;
        margin: 0.5rem 0 1.2rem 0;
        font-size: 0.92rem;
        font-weight: 500;
        line-height: 1.6;
        box-shadow: 0 4px 20px rgba(74, 222, 128, 0.10), inset 0 1px 0 rgba(74,222,128,0.12);
        border: 1px solid rgba(74, 222, 128, 0.18);
        border-top: 1px solid rgba(74, 222, 128, 0.32);
        letter-spacing: -0.01em;
    ">{icon}&nbsp;&nbsp;{text}</div>
    """


def warning_box(text: str):
    return f"""
    <div style="
        background: rgba(239, 68, 68, 0.08);
        color: #FCA5A5;
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-top: 1px solid rgba(239, 68, 68, 0.4);
        padding: 0.85rem 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    ">⚠️&nbsp;&nbsp;{text}</div>
    """


def roas_box(value: float) -> str:
    if value >= 3:
        return f"""
        <div style="background:rgba(74,222,128,0.07);color:#86EFAC;
        border:1px solid rgba(74,222,128,0.20);border-top:1px solid rgba(74,222,128,0.35);
        padding:0.85rem 1.2rem;border-radius:12px;margin:0.5rem 0;font-size:0.9rem;">
        🟢 ROAS de {value:.2f}x — retorno saudável sobre o investimento.</div>
        """
    elif value >= 1:
        return f"""
        <div style="background:rgba(245,158,11,0.08);color:#FCD34D;
        border:1px solid rgba(245,158,11,0.25);border-top:1px solid rgba(245,158,11,0.4);
        padding:0.85rem 1.2rem;border-radius:12px;margin:0.5rem 0;font-size:0.9rem;">
        🟡 ROAS de {value:.2f}x — positivo, mas há espaço para otimização.</div>
        """
    else:
        return warning_box(f"ROAS de {value:.2f}x — investimento não está sendo recuperado. Atenção necessária.")


def section_header(title: str, subtitle: str = ""):
    sub = f'<span style="color:#3E5E3E;font-size:0.78rem;font-weight:400;margin-left:0.5rem;">{subtitle}</span>' if subtitle else ""
    return f"""
    <div style="
        display: flex;
        align-items: center;
        margin: 1.6rem 0 0.7rem;
        gap: 0.6rem;
    ">
        <div style="width:3px;height:1.1rem;background:linear-gradient(180deg,#4ADE80,rgba(74,222,128,0.2));border-radius:2px;flex-shrink:0;"></div>
        <span style="font-weight:600;font-size:0.88rem;color:#ECFDF5;letter-spacing:-0.01em;">{title}</span>
        {sub}
    </div>
    """
