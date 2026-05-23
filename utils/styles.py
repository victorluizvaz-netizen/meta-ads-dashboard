def css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* ── Animações ────────────────────────────────────────────────── */
        @keyframes fade-in-up {
            from { opacity: 0; transform: translateY(12px); }
            to   { opacity: 1; transform: translateY(0);    }
        }
        @keyframes fade-in {
            from { opacity: 0; }
            to   { opacity: 1; }
        }
        @keyframes gold-pulse {
            0%, 100% { box-shadow: 0 0 0   0   rgba(245,158,11,0.45); }
            50%      { box-shadow: 0 0 14px 4px rgba(245,158,11,0);    }
        }

        /* Entrada da página — dispara em toda navegação */
        section[data-testid="stMain"] > div > div:first-child {
            animation: fade-in-up 0.38s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        /* Gráficos Plotly — fade-in com leve atraso */
        div[data-testid="stPlotlyChart"] {
            animation: fade-in 0.55s cubic-bezier(0.16, 1, 0.3, 1) 0.06s both;
        }

        /* Cards de métrica */
        div[data-testid="metric-container"] {
            animation: fade-in-up 0.42s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        /* ── CSS variables ────────────────────────────────────────────── */
        :root {
            --accent:        #38BDF8;
            --accent-light:  #7DD3FC;
            --accent-strong: #0EA5E9;
            --gold:          #F59E0B;
            --gold-light:    #FCD34D;
            --surface-1:     #050C1A;
            --surface-2:     #080F1E;
            --border:        rgba(56, 189, 248, 0.10);
            --border-hi:     rgba(56, 189, 248, 0.28);
            --text-primary:  #EFF6FF;
            --text-secondary:#7FA8C9;
            --text-muted:    #2A4A6E;
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
            background: rgba(56, 189, 248, 0.22);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: rgba(56, 189, 248, 0.44); }

        /* ── Typography ───────────────────────────────────────────────── */
        h1 {
            font-size: 1.7rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            color: var(--text-primary) !important;
            background: linear-gradient(90deg, #EFF6FF 25%, #7DD3FC 72%, #FCD34D 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        h2, h3 { color: var(--text-primary) !important; }

        /* ── Sidebar ──────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #030810 0%, #050C1A 100%) !important;
            border-right: 1px solid rgba(56, 189, 248, 0.08) !important;
        }
        section[data-testid="stSidebar"] > div { background: transparent !important; }
        .stSidebar .stCaption { color: var(--text-muted) !important; }
        .stSidebar label      { color: var(--text-secondary) !important; }

        /* ── Metric cards ─────────────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: linear-gradient(160deg, #0C1428 0%, #080F1E 100%);
            border: 1px solid var(--border);
            border-top: 2px solid rgba(56, 189, 248, 0.28);
            border-radius: 16px;
            padding: 1.2rem 1.4rem 1.1rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.025);
            transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
            position: relative;
            overflow: hidden;
        }
        div[data-testid="metric-container"]::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, #38BDF8, #F59E0B);
            border-radius: 16px 16px 0 0;
            opacity: 0.78;
        }
        div[data-testid="metric-container"]:hover {
            border-color: rgba(56, 189, 248, 0.24);
            box-shadow: 0 8px 32px rgba(0,0,0,0.65), 0 0 28px rgba(56,189,248,0.07),
                        inset 0 1px 0 rgba(255,255,255,0.04);
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
            background: linear-gradient(160deg, #0C1428 0%, #080F1E 100%);
            border: 1px solid var(--border);
            border-top: 1px solid rgba(56, 189, 248, 0.16);
            border-radius: 16px;
            padding: 0.4rem 0.2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.45);
            transition: border-color 0.25s ease, box-shadow 0.25s ease;
        }
        div[data-testid="stPlotlyChart"]:hover {
            border-color: rgba(56, 189, 248, 0.18);
            box-shadow: 0 8px 28px rgba(0,0,0,0.55), 0 0 20px rgba(56,189,248,0.05);
        }

        /* ── Dividers ─────────────────────────────────────────────────── */
        hr {
            border: none !important;
            border-top: 1px solid rgba(56, 189, 248, 0.07) !important;
            margin: 1.5rem 0 !important;
        }

        /* ── Expander ─────────────────────────────────────────────────── */
        details {
            background: linear-gradient(160deg, #0A1020 0%, #060D1A 100%) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
        }
        details[open] { border-color: rgba(56, 189, 248, 0.18) !important; }
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
        .stSpinner > div { border-top-color: #38BDF8 !important; }

        /* ── Tabs ─────────────────────────────────────────────────────── */
        button[data-baseweb="tab"] {
            font-size: 0.84rem !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] { color: #7DD3FC !important; }
        div[data-baseweb="tab-highlight"] {
            background: linear-gradient(90deg, #38BDF8, #F59E0B) !important;
            height: 2px !important;
            border-radius: 2px !important;
        }
        div[data-baseweb="tab-border"] { background: rgba(56, 189, 248, 0.08) !important; }

        /* ── Input fields ─────────────────────────────────────────────── */
        div[data-baseweb="select"] > div {
            background: #080F1E !important;
            border-color: rgba(56, 189, 248, 0.16) !important;
            border-radius: 10px !important;
        }
        div[data-baseweb="input"] > div {
            background: #080F1E !important;
            border-color: rgba(56, 189, 248, 0.16) !important;
            border-radius: 10px !important;
        }

        /* ── Multiselect tag ──────────────────────────────────────────── */
        span[data-baseweb="tag"] {
            background: rgba(56, 189, 248, 0.14) !important;
            border: 1px solid rgba(56, 189, 248, 0.28) !important;
            border-radius: 6px !important;
            color: #7DD3FC !important;
        }

        /* ── Date input ───────────────────────────────────────────────── */
        div[data-testid="stDateInput"] input {
            background: #080F1E !important;
            border-color: rgba(56, 189, 248, 0.16) !important;
            border-radius: 10px !important;
        }

        /* ── Alert boxes ──────────────────────────────────────────────── */
        div[data-testid="stAlert"] { border-radius: 12px !important; }

        /* ── Buttons ──────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #0369A1, #0EA5E9) !important;
            border: none !important;
            border-radius: 10px !important;
            color: white !important;
            font-weight: 600 !important;
            transition: opacity 0.18s, transform 0.15s !important;
        }
        .stButton > button:hover {
            opacity: 0.88 !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button:active {
            transform: translateY(0) scale(0.97) !important;
        }
    </style>
    """


def insight_box(text: str, icon: str = "💡"):
    return f"""
    <div style="
        background: linear-gradient(135deg, rgba(3,105,161,0.35) 0%, rgba(14,165,233,0.18) 100%);
        color: #BAE6FD;
        padding: 0.95rem 1.4rem;
        border-radius: 14px;
        margin: 0.5rem 0 1.2rem 0;
        font-size: 0.92rem;
        font-weight: 500;
        line-height: 1.6;
        box-shadow: 0 4px 20px rgba(56,189,248,0.10), inset 0 1px 0 rgba(56,189,248,0.12);
        border: 1px solid rgba(56, 189, 248, 0.20);
        border-top: 1px solid rgba(56, 189, 248, 0.36);
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
        <div style="background:rgba(56,189,248,0.08);color:#BAE6FD;
        border:1px solid rgba(56,189,248,0.20);border-top:1px solid rgba(56,189,248,0.36);
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
    sub = (
        f'<span style="color:#2A4A6E;font-size:0.78rem;font-weight:400;margin-left:0.5rem;">'
        f'{subtitle}</span>'
    ) if subtitle else ""
    return f"""
    <div style="display:flex;align-items:center;margin:1.6rem 0 0.7rem;gap:0.6rem;">
        <div style="width:3px;height:1.1rem;
                    background:linear-gradient(180deg,#38BDF8,rgba(245,158,11,0.30));
                    border-radius:2px;flex-shrink:0;"></div>
        <span style="font-weight:700;font-size:0.88rem;color:#EFF6FF;letter-spacing:-0.01em;">{title}</span>
        {sub}
    </div>
    """
