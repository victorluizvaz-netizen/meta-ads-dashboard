def css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        .block-container {
            padding-top: 1.5rem !important;
        }

        /* ── Metric cards ─────────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: #161929;
            border: 1px solid rgba(108, 99, 255, 0.14);
            border-radius: 14px;
            padding: 1.1rem 1.3rem;
            box-shadow: 0 0 0 1px rgba(255,255,255,0.03), 0 4px 24px rgba(0,0,0,0.35);
            transition: border-color 0.2s ease;
        }

        div[data-testid="metric-container"]:hover {
            border-color: rgba(108, 99, 255, 0.38);
        }

        div[data-testid="metric-container"] label {
            color: #7C8DB5 !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        div[data-testid="stMetricValue"] > div {
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            color: #F1F5F9 !important;
        }

        /* ── Dividers ─────────────────────────────────────────────── */
        hr {
            border-color: rgba(255,255,255,0.06) !important;
            margin: 1rem 0 !important;
        }

        /* ── Expander ─────────────────────────────────────────────── */
        details {
            background: #161929 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 12px !important;
            padding: 0.2rem 0 !important;
        }

        details summary {
            color: #94A3B8 !important;
            font-size: 0.88rem !important;
        }

        /* ── Spinner text ─────────────────────────────────────────── */
        .stSpinner > div {
            border-top-color: #6C63FF !important;
        }

        /* ── Sidebar caption ──────────────────────────────────────── */
        .stSidebar .stCaption {
            color: #5A6A8A !important;
        }

        /* ── Multiselect tag ──────────────────────────────────────── */
        span[data-baseweb="tag"] {
            background: rgba(108, 99, 255, 0.2) !important;
            border: 1px solid rgba(108, 99, 255, 0.35) !important;
            border-radius: 6px !important;
        }
    </style>
    """


def insight_box(text: str, icon: str = "💡"):
    return f"""
    <div style="
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        color: #F1F5F9;
        padding: 0.9rem 1.4rem;
        border-radius: 12px;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.93rem;
        font-weight: 500;
        line-height: 1.55;
        box-shadow: 0 4px 20px rgba(108, 99, 255, 0.25);
        border: 1px solid rgba(108, 99, 255, 0.25);
    ">{icon}&nbsp;&nbsp;{text}</div>
    """


def warning_box(text: str):
    return f"""
    <div style="
        background: rgba(239, 68, 68, 0.1);
        color: #FCA5A5;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 0.8rem 1.2rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    ">⚠️&nbsp;&nbsp;{text}</div>
    """


def roas_box(value: float) -> str:
    if value >= 3:
        return f"""
        <div style="background:rgba(16,185,129,0.1);color:#6EE7B7;border:1px solid rgba(16,185,129,0.3);
        padding:0.8rem 1.2rem;border-radius:10px;margin:0.5rem 0;font-size:0.9rem;">
        🟢 ROAS de {value:.2f}x — retorno saudável sobre o investimento.</div>
        """
    elif value >= 1:
        return f"""
        <div style="background:rgba(245,158,11,0.1);color:#FCD34D;border:1px solid rgba(245,158,11,0.3);
        padding:0.8rem 1.2rem;border-radius:10px;margin:0.5rem 0;font-size:0.9rem;">
        🟡 ROAS de {value:.2f}x — positivo, mas há espaço para otimização.</div>
        """
    else:
        return warning_box(f"ROAS de {value:.2f}x — investimento não está sendo recuperado. Atenção necessária.")


def section_header(title: str, subtitle: str = ""):
    sub = f'<p style="color:#5A6A8A;font-size:0.82rem;margin:0.2rem 0 0;">{subtitle}</p>' if subtitle else ""
    return f"""
    <div style="margin:1.2rem 0 0.8rem;">
        <p style="font-weight:600;font-size:1rem;margin:0;color:#F1F5F9;">{title}</p>
        {sub}
    </div>
    """
