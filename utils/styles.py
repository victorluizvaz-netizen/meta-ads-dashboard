def css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* ── CSS variables ────────────────────────────────────────────── */
        :root {
            --accent:        #A855F7;
            --accent-light:  #C084FC;
            --accent-strong: #9333EA;
            --pink:          #EC4899;
            --pink-light:    #F9A8D4;
            --surface-1:     #130E27;
            --surface-2:     #1A1438;
            --border:        rgba(168, 85, 247, 0.12);
            --border-hi:     rgba(168, 85, 247, 0.32);
            --text-primary:  #F1ECF8;
            --text-secondary:#8B7EAF;
            --text-muted:    #5B4E7A;
        }

        /* ── Layout ───────────────────────────────────────────────────── */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
        }

        /* ── Scrollbar ────────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: rgba(168, 85, 247, 0.25);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: rgba(168, 85, 247, 0.50); }

        /* ── Typography ───────────────────────────────────────────────── */
        h1 {
            font-size: 1.7rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            color: var(--text-primary) !important;
            background: linear-gradient(90deg, #F1ECF8 30%, #C084FC 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        h2, h3 {
            color: var(--text-primary) !important;
        }

        /* ── Sidebar ──────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0A0718 0%, #0D0B1A 100%) !important;
            border-right: 1px solid rgba(168, 85, 247, 0.10) !important;
        }
        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        .stSidebar .stCaption { color: var(--text-muted) !important; }
        .stSidebar label { color: var(--text-secondary) !important; }

        /* ── Metric cards ─────────────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: linear-gradient(160deg, #160D30 0%, #110B24 100%);
            border: 1px solid var(--border);
            border-top: 2px solid rgba(168, 85, 247, 0.35);
            border-radius: 16px;
            padding: 1.2rem 1.4rem 1.1rem;
            box-shadow:
                0 4px 24px rgba(0,0,0,0.55),
                0 0 0 0 rgba(168,85,247,0),
                inset 0 1px 0 rgba(255,255,255,0.03);
            transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
            position: relative;
            overflow: hidden;
        }
        div[data-testid="metric-container"]::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, #A855F7, #EC4899);
            border-radius: 16px 16px 0 0;
            opacity: 0.7;
        }
        div[data-testid="metric-container"]:hover {
            border-color: rgba(168, 85, 247, 0.30);
            box-shadow:
                0 8px 32px rgba(0,0,0,0.65),
                0 0 28px rgba(168, 85, 247, 0.10),
                inset 0 1px 0 rgba(255,255,255,0.05);
            transform: translateY(-3px);
        }
        div[data-testid="metric-container"] label {
            color: var(--text-muted) !important;
            font-size: 0.69rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.10em;
        }
        div[data-testid="stMetricValue"] > div {
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            color: var(--text-primary) !important;
            letter-spacing: -0.025em !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stMetricDelta"] {
            font-size: 0.76rem !important;
            font-weight: 500 !important;
            opacity: 0.85;
        }

        /* ── Chart panels ─────────────────────────────────────────────── */
        div[data-testid="stPlotlyChart"] {
            background: linear-gradient(160deg, #160D30 0%, #110B24 100%);
            border: 1px solid var(--border);
            border-top: 1px solid rgba(168, 85, 247, 0.18);
            border-radius: 16px;
            padding: 0.4rem 0.2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.45);
            transition: border-color 0.25s ease, box-shadow 0.25s ease;
        }
        div[data-testid="stPlotlyChart"]:hover {
            border-color: rgba(168, 85, 247, 0.22);
            box-shadow: 0 8px 28px rgba(0,0,0,0.55), 0 0 20px rgba(168,85,247,0.06);
        }

        /* ── Dividers ─────────────────────────────────────────────────── */
        hr {
            border: none !important;
            border-top: 1px solid rgba(168, 85, 247, 0.08) !important;
            margin: 1.5rem 0 !important;
        }

        /* ── Expander ─────────────────────────────────────────────────── */
        details {
            background: linear-gradient(160deg, #160D30 0%, #110B24 100%) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
        }
        details[open] { border-color: rgba(168, 85, 247, 0.20) !important; }
        details summary {
            color: var(--text-secondary) !important;
            font-size: 0.87rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 0 !important;
        }

        /* ── Dataframe ────────────────────────────────────────────────── */
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            overflow: hidden;
        }

        /* ── Spinner ──────────────────────────────────────────────────── */
        .stSpinner > div { border-top-color: #A855F7 !important; }

        /* ── Tabs ─────────────────────────────────────────────────────── */
        button[data-baseweb="tab"] {
            font-size: 0.84rem !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #C084FC !important;
        }
        div[data-baseweb="tab-highlight"] {
            background: linear-gradient(90deg, #A855F7, #EC4899) !important;
            height: 2px !important;
            border-radius: 2px !important;
        }
        div[data-baseweb="tab-border"] {
            background: rgba(168, 85, 247, 0.10) !important;
        }

        /* ── Input fields ─────────────────────────────────────────────── */
        div[data-baseweb="select"] > div {
            background: #110B24 !important;
            border-color: rgba(168, 85, 247, 0.18) !important;
            border-radius: 10px !important;
        }
        div[data-baseweb="input"] > div {
            background: #110B24 !important;
            border-color: rgba(168, 85, 247, 0.18) !important;
            border-radius: 10px !important;
        }

        /* ── Multiselect tag ──────────────────────────────────────────── */
        span[data-baseweb="tag"] {
            background: rgba(168, 85, 247, 0.15) !important;
            border: 1px solid rgba(168, 85, 247, 0.30) !important;
            border-radius: 6px !important;
            color: #C084FC !important;
        }

        /* ── Date input ───────────────────────────────────────────────── */
        div[data-testid="stDateInput"] input {
            background: #110B24 !important;
            border-color: rgba(168, 85, 247, 0.18) !important;
            border-radius: 10px !important;
        }

        /* ── Alert boxes ──────────────────────────────────────────────── */
        div[data-testid="stAlert"] {
            border-radius: 12px !important;
        }

        /* ── Buttons ──────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #7C3AED, #A855F7) !important;
            border: none !important;
            border-radius: 10px !important;
            color: white !important;
            font-weight: 600 !important;
            transition: opacity 0.2s, transform 0.2s !important;
        }
        .stButton > button:hover {
            opacity: 0.88 !important;
            transform: translateY(-1px) !important;
        }
    </style>
    """


def insight_box(text: str, icon: str = "💡"):
    return f"""
    <div style="
        background: linear-gradient(135deg, rgba(88,28,135,0.40) 0%, rgba(109,40,217,0.22) 100%);
        color: #DDD6FE;
        padding: 0.95rem 1.4rem;
        border-radius: 14px;
        margin: 0.5rem 0 1.2rem 0;
        font-size: 0.92rem;
        font-weight: 500;
        line-height: 1.6;
        box-shadow: 0 4px 20px rgba(168,85,247,0.12), inset 0 1px 0 rgba(168,85,247,0.15);
        border: 1px solid rgba(168, 85, 247, 0.22);
        border-top: 1px solid rgba(168, 85, 247, 0.40);
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
        <div style="background:rgba(168,85,247,0.09);color:#DDD6FE;
        border:1px solid rgba(168,85,247,0.22);border-top:1px solid rgba(168,85,247,0.40);
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
    sub = f'<span style="color:#5B4E7A;font-size:0.78rem;font-weight:400;margin-left:0.5rem;">{subtitle}</span>' if subtitle else ""
    return f"""
    <div style="
        display: flex;
        align-items: center;
        margin: 1.6rem 0 0.7rem;
        gap: 0.6rem;
    ">
        <div style="width:3px;height:1.1rem;background:linear-gradient(180deg,#A855F7,rgba(236,72,153,0.3));border-radius:2px;flex-shrink:0;"></div>
        <span style="font-weight:700;font-size:0.88rem;color:#F1ECF8;letter-spacing:-0.01em;">{title}</span>
        {sub}
    </div>
    """
