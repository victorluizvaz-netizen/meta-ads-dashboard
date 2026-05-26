def css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* ── Animações ─────────────────────────────────────────────────── */
        @keyframes fade-in-up {
            from { opacity: 0; transform: translateY(16px); }
            to   { opacity: 1; transform: translateY(0);    }
        }
        @keyframes fade-in {
            from { opacity: 0; }
            to   { opacity: 1; }
        }
        @keyframes shimmer {
            0%   { background-position: -200% center; }
            100% { background-position:  200% center; }
        }
        @keyframes glow-pulse {
            0%, 100% { box-shadow: 0 0 0   0   rgba(56,189,248,0.0); }
            50%      { box-shadow: 0 0 22px 4px rgba(56,189,248,0.12); }
        }
        @keyframes border-glow {
            0%, 100% { border-top-color: rgba(56,189,248,0.28); }
            50%      { border-top-color: rgba(56,189,248,0.55); }
        }
        @keyframes slide-in-right {
            from { opacity: 0; transform: translateX(18px); }
            to   { opacity: 1; transform: translateX(0);    }
        }

        /* Entrada da página */
        section[data-testid="stMain"] > div > div:first-child {
            animation: fade-in-up 0.42s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        /* Gráficos Plotly */
        div[data-testid="stPlotlyChart"] {
            animation: fade-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both;
        }

        /* Cards de métrica */
        div[data-testid="metric-container"] {
            animation: fade-in-up 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        /* ── CSS variables ─────────────────────────────────────────────── */
        :root {
            --accent:        #38BDF8;
            --accent-light:  #7DD3FC;
            --accent-strong: #0EA5E9;
            --gold:          #F59E0B;
            --gold-light:    #FCD34D;
            --surface-0:     #030810;
            --surface-1:     #050C1A;
            --surface-2:     #080F1E;
            --surface-3:     #0C1428;
            --border:        rgba(56, 189, 248, 0.10);
            --border-hi:     rgba(56, 189, 248, 0.28);
            --text-primary:  #EFF6FF;
            --text-secondary:#7FA8C9;
            --text-muted:    #2A4A6E;
            --glass-bg:      rgba(8, 15, 30, 0.72);
            --glass-border:  rgba(56, 189, 248, 0.12);
        }

        /* ── Layout ────────────────────────────────────────────────────── */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 100% !important;
        }

        /* ── Scrollbar ─────────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: rgba(56, 189, 248, 0.20);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: rgba(56, 189, 248, 0.40); }

        /* ── Typography ────────────────────────────────────────────────── */
        h1 {
            font-size: 1.75rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.035em !important;
            background: linear-gradient(
                90deg,
                #EFF6FF 0%,
                #7DD3FC 35%,
                #38BDF8 50%,
                #FCD34D 70%,
                #F59E0B 85%,
                #EFF6FF 100%
            );
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: shimmer 4s linear infinite;
        }
        h2 { color: #BAE6FD !important; font-weight: 700 !important; }
        h3 { color: var(--text-primary) !important; font-weight: 600 !important; }

        /* ── Sidebar ───────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #020710 0%, #030C1A 60%, #050C1A 100%) !important;
            border-right: 1px solid rgba(56, 189, 248, 0.07) !important;
        }
        section[data-testid="stSidebar"] > div { background: transparent !important; }
        .stSidebar .stCaption { color: var(--text-muted) !important; }
        .stSidebar label      { color: var(--text-secondary) !important; }

        /* Links de navegação da sidebar */
        section[data-testid="stSidebar"] a {
            color: var(--text-secondary) !important;
            text-decoration: none !important;
            font-size: 0.85rem !important;
            transition: color 0.2s ease !important;
        }
        section[data-testid="stSidebar"] a:hover {
            color: var(--accent-light) !important;
        }

        /* ── Metric cards ──────────────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: linear-gradient(145deg, #0D1830 0%, #080F1E 60%, #050C1A 100%);
            border: 1px solid rgba(56, 189, 248, 0.10);
            border-top: 2px solid rgba(56, 189, 248, 0.30);
            border-radius: 18px;
            padding: 1.25rem 1.4rem 1.15rem;
            box-shadow:
                0 4px 24px rgba(0,0,0,0.60),
                0 1px 0 rgba(255,255,255,0.02) inset,
                0 0 0 0 rgba(56,189,248,0.0);
            transition:
                border-color 0.3s ease,
                box-shadow 0.3s ease,
                transform 0.28s cubic-bezier(0.34,1.56,0.64,1);
            position: relative;
            overflow: hidden;
            animation: border-glow 3.5s ease-in-out infinite;
        }
        div[data-testid="metric-container"]::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #38BDF8 30%, #F59E0B 70%, transparent);
            border-radius: 18px 18px 0 0;
            opacity: 0.85;
        }
        div[data-testid="metric-container"]::after {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(ellipse at 50% 0%, rgba(56,189,248,0.04) 0%, transparent 70%);
            pointer-events: none;
        }
        div[data-testid="metric-container"]:hover {
            border-color: rgba(56, 189, 248, 0.28);
            box-shadow:
                0 12px 40px rgba(0,0,0,0.70),
                0 0 32px rgba(56,189,248,0.10),
                0 1px 0 rgba(255,255,255,0.04) inset;
            transform: translateY(-4px);
        }
        div[data-testid="metric-container"] label {
            color: var(--text-muted) !important;
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }
        div[data-testid="stMetricValue"] > div {
            font-size: 1.6rem !important;
            font-weight: 800 !important;
            color: var(--text-primary) !important;
            letter-spacing: -0.03em !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stMetricDelta"] {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            opacity: 0.9;
        }

        /* ── Chart panels ──────────────────────────────────────────────── */
        div[data-testid="stPlotlyChart"] {
            background: linear-gradient(160deg, #0C1830 0%, #080F1E 100%);
            border: 1px solid rgba(56, 189, 248, 0.09);
            border-top: 1px solid rgba(56, 189, 248, 0.18);
            border-radius: 18px;
            padding: 0.5rem 0.3rem 0.3rem;
            box-shadow:
                0 4px 24px rgba(0,0,0,0.50),
                0 0 0 0 rgba(56,189,248,0.0);
            transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.28s ease;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }
        div[data-testid="stPlotlyChart"]:hover {
            border-color: rgba(56, 189, 248, 0.20);
            box-shadow:
                0 8px 36px rgba(0,0,0,0.60),
                0 0 28px rgba(56,189,248,0.07);
            transform: translateY(-2px);
        }

        /* ── Glassmorphism containers ──────────────────────────────────── */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--glass-bg) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 16px !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.02) !important;
        }

        /* ── Dividers ──────────────────────────────────────────────────── */
        hr {
            border: none !important;
            border-top: 1px solid rgba(56, 189, 248, 0.07) !important;
            margin: 1.5rem 0 !important;
        }

        /* ── Expander / glassmorphism ──────────────────────────────────── */
        details {
            background: rgba(8, 15, 30, 0.70) !important;
            border: 1px solid rgba(56, 189, 248, 0.10) !important;
            border-radius: 14px !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            box-shadow: 0 2px 12px rgba(0,0,0,0.35) !important;
        }
        details[open] {
            border-color: rgba(56, 189, 248, 0.20) !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.45), 0 0 16px rgba(56,189,248,0.04) !important;
        }
        details summary {
            color: var(--text-secondary) !important;
            font-size: 0.87rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 0 !important;
        }

        /* ── Dataframe ─────────────────────────────────────────────────── */
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(56, 189, 248, 0.10) !important;
            border-radius: 14px !important;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.40) !important;
        }

        /* ── Spinner ───────────────────────────────────────────────────── */
        .stSpinner > div { border-top-color: #38BDF8 !important; }

        /* ── Tabs ──────────────────────────────────────────────────────── */
        button[data-baseweb="tab"] {
            font-size: 0.84rem !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            transition: color 0.2s ease !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #7DD3FC !important;
            font-weight: 600 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background: linear-gradient(90deg, #38BDF8, #F59E0B) !important;
            height: 2px !important;
            border-radius: 2px !important;
        }
        div[data-baseweb="tab-border"] { background: rgba(56, 189, 248, 0.07) !important; }

        /* ── Input fields ──────────────────────────────────────────────── */
        div[data-baseweb="select"] > div {
            background: rgba(8, 15, 30, 0.80) !important;
            border-color: rgba(56, 189, 248, 0.15) !important;
            border-radius: 10px !important;
            transition: border-color 0.2s ease !important;
        }
        div[data-baseweb="select"] > div:focus-within {
            border-color: rgba(56, 189, 248, 0.40) !important;
            box-shadow: 0 0 0 3px rgba(56,189,248,0.08) !important;
        }
        div[data-baseweb="input"] > div {
            background: rgba(8, 15, 30, 0.80) !important;
            border-color: rgba(56, 189, 248, 0.15) !important;
            border-radius: 10px !important;
            transition: border-color 0.2s ease !important;
        }
        div[data-baseweb="input"] > div:focus-within {
            border-color: rgba(56, 189, 248, 0.40) !important;
            box-shadow: 0 0 0 3px rgba(56,189,248,0.08) !important;
        }

        /* ── Multiselect tag ───────────────────────────────────────────── */
        span[data-baseweb="tag"] {
            background: rgba(56, 189, 248, 0.12) !important;
            border: 1px solid rgba(56, 189, 248, 0.26) !important;
            border-radius: 6px !important;
            color: #7DD3FC !important;
        }

        /* ── Date input ────────────────────────────────────────────────── */
        div[data-testid="stDateInput"] input {
            background: rgba(8, 15, 30, 0.80) !important;
            border-color: rgba(56, 189, 248, 0.15) !important;
            border-radius: 10px !important;
        }

        /* ── Alert boxes ───────────────────────────────────────────────── */
        div[data-testid="stAlert"] { border-radius: 12px !important; }

        /* ── Buttons ───────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #0369A1 0%, #0EA5E9 100%) !important;
            border: none !important;
            border-radius: 10px !important;
            color: white !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 2px 12px rgba(14,165,233,0.25) !important;
            transition: opacity 0.18s ease, transform 0.15s ease, box-shadow 0.2s ease !important;
        }
        .stButton > button:hover {
            opacity: 0.92 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 22px rgba(14,165,233,0.40) !important;
        }
        .stButton > button:active {
            transform: translateY(0) scale(0.97) !important;
            box-shadow: 0 2px 8px rgba(14,165,233,0.20) !important;
        }
    </style>
    """


def insight_box(text: str, icon: str = "💡"):
    return f"""
    <div style="
        background: linear-gradient(135deg, rgba(3,105,161,0.30) 0%, rgba(14,165,233,0.14) 100%);
        color: #BAE6FD;
        padding: 0.95rem 1.4rem;
        border-radius: 14px;
        margin: 0.5rem 0 1.2rem 0;
        font-size: 0.92rem;
        font-weight: 500;
        line-height: 1.65;
        box-shadow: 0 4px 20px rgba(56,189,248,0.08), inset 0 1px 0 rgba(56,189,248,0.10);
        border: 1px solid rgba(56, 189, 248, 0.16);
        border-top: 1px solid rgba(56, 189, 248, 0.34);
        letter-spacing: -0.01em;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    ">{icon}&nbsp;&nbsp;{text}</div>
    """


def warning_box(text: str):
    return f"""
    <div style="
        background: rgba(239, 68, 68, 0.07);
        color: #FCA5A5;
        border: 1px solid rgba(239, 68, 68, 0.22);
        border-top: 1px solid rgba(239, 68, 68, 0.38);
        padding: 0.85rem 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    ">⚠️&nbsp;&nbsp;{text}</div>
    """


def roas_box(value: float) -> str:
    if value >= 3:
        return f"""
        <div style="background:rgba(16,185,129,0.07);color:#6EE7B7;
        border:1px solid rgba(16,185,129,0.20);border-top:1px solid rgba(16,185,129,0.38);
        padding:0.85rem 1.2rem;border-radius:12px;margin:0.5rem 0;font-size:0.9rem;
        backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);">
        🟢 ROAS de {value:.2f}x — retorno saudável sobre o investimento.</div>
        """
    elif value >= 1:
        return f"""
        <div style="background:rgba(245,158,11,0.07);color:#FCD34D;
        border:1px solid rgba(245,158,11,0.22);border-top:1px solid rgba(245,158,11,0.38);
        padding:0.85rem 1.2rem;border-radius:12px;margin:0.5rem 0;font-size:0.9rem;
        backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);">
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
    <div style="display:flex;align-items:center;margin:1.8rem 0 0.8rem;gap:0.7rem;">
        <div style="width:3px;height:1.15rem;
                    background:linear-gradient(180deg,#38BDF8 0%,rgba(245,158,11,0.35) 100%);
                    border-radius:2px;flex-shrink:0;
                    box-shadow:0 0 8px rgba(56,189,248,0.35);"></div>
        <span style="font-weight:700;font-size:0.88rem;color:#EFF6FF;letter-spacing:-0.01em;">{title}</span>
        {sub}
    </div>
    """
