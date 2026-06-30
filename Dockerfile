# Imagem só para a API FastAPI (api/main.py), para deploy no Railway.
# Instala apenas as dependências da API (sem streamlit/weasyprint).
# O Streamlit Community Cloud ignora este arquivo (usa requirements.txt + packages.txt).
FROM python:3.12-slim

WORKDIR /app

# Dependências enxutas da API
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r api/requirements.txt

# Código (api/ + utils/, que a API importa)
COPY . .

# Railway injeta $PORT; default 8000 para rodar local
ENV PORT=8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
