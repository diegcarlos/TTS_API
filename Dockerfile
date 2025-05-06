FROM python:3.10-slim

WORKDIR /app

# Instalar dependências para a compilação e execução
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    libsndfile1 \
    alsa-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de requisitos
COPY requirements.txt .

# Instalar as dependências
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baixar o modelo XTTS v2 usando huggingface_hub
RUN pip install --no-cache-dir huggingface_hub && \
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='coqui/XTTS-v2', local_dir='/root/.local/share/TTS/tts_models/multilingual/multi-dataset/xtts_v2')"

# Copiar o código da aplicação
COPY . .

# Criar diretório de cache se não existir
RUN mkdir -p cache_audio/senha cache_audio/guiche

# Expor a porta onde a API estará disponível
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["python", "run_server.py", "--host", "0.0.0.0", "--port", "8000"] 