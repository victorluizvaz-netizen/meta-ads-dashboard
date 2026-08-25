# Imagem só para a API FastAPI (api/main.py), para deploy no Railway.
# Instala as dependências da API (sem streamlit) + pandas/plotly/weasyprint,
# usadas só pelo endpoint /api/campaign-report (geração de relatório de campanha).
# O Streamlit Community Cloud ignora este arquivo (usa requirements.txt + packages.txt).
FROM python:3.12-slim

WORKDIR /app

# Libs nativas do weasyprint (mesmas do packages.txt do lado Streamlit Cloud) —
# necessárias pro endpoint /api/campaign-report gerar PDF.
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependências enxutas da API
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r api/requirements.txt

# Código (api/ + utils/, que a API importa)
COPY . .

# Railway injeta $PORT; default 8000 para rodar local
ENV PORT=8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
