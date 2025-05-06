import torch
import os
import numpy as np
import hashlib
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional
from TTS.api import TTS as TTSObject
from torch.serialization import add_safe_globals
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig

# Adicionar todas as classes conhecidas aos globais seguros
add_safe_globals([
    XttsConfig, 
    XttsAudioConfig, 
    BaseDatasetConfig,
    XttsArgs
])

# Modificar diretamente o comportamento do torch.load
original_torch_load = torch.load

def patched_torch_load(f, map_location=None, pickle_module=None, **pickle_load_args):
    # Forçar weights_only=False para carregar o modelo XTTS
    if 'weights_only' not in pickle_load_args:
        pickle_load_args['weights_only'] = False
    return original_torch_load(f, map_location, pickle_module, **pickle_load_args)

# Aplicar o patch
torch.load = patched_torch_load

# Configuração do cache
CACHE_DIR = "cache_audio"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Diretórios específicos para componentes
SENHA_DIR = os.path.join(CACHE_DIR, "senha")
GUICHE_DIR = os.path.join(CACHE_DIR, "guiche")

# Criar diretórios se não existirem
if not os.path.exists(SENHA_DIR):
    os.makedirs(SENHA_DIR)

if not os.path.exists(GUICHE_DIR):
    os.makedirs(GUICHE_DIR)

# JSON para registro de metadados do cache
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, "cache_index.json")
if os.path.exists(CACHE_INDEX_FILE):
    try:
        with open(CACHE_INDEX_FILE, 'r', encoding='utf-8') as f:
            cache_index = json.load(f)
    except:
        cache_index = {}
else:
    cache_index = {}

def save_cache_index():
    """Salva o índice de cache no arquivo JSON"""
    with open(CACHE_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_index, f, ensure_ascii=False, indent=2)

# Get device
device = "cuda" if torch.cuda.is_available() else "cpu"

# List available 🐸TTS models
print(TTSObject().list_models())

# Init TTS
tts = TTSObject("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# Falantes padrão por idioma - definir falantes que soam bem para cada idioma
DEFAULT_SPEAKERS = {
    "pt": "Alma María",  # Falante para português
    "en": "Nova Hogarth",  # Falante para inglês
    "es": "Alma María",  # Falante para espanhol
    "fr": "Alison Dietlinde",  # Falante para francês
    "de": "Alison Dietlinde",  # Falante para alemão
    "it": "Ana Florence",  # Falante para italiano
    "default": "Nova Hogarth"  # Falante padrão para outras línguas
}

# Obter a lista de falantes disponíveis no modelo
try:
    available_speakers = list(tts.synthesizer.tts_model.speaker_manager.speakers.keys())
    print(f"Falantes disponíveis: {available_speakers}")
except Exception as e:
    print(f"Não foi possível obter a lista de falantes: {str(e)}")
    available_speakers = []

app = FastAPI(
    title="TTS API",
    description="API para síntese de voz e chamada de guichê",
    version="1.0.0",
)

# Montar diretórios estáticos para servir os arquivos de áudio
app.mount("/audio", StaticFiles(directory=CACHE_DIR), name="audio")
app.mount("/senha", StaticFiles(directory=SENHA_DIR), name="senha")
app.mount("/guiche", StaticFiles(directory=GUICHE_DIR), name="guiche")

# Função para obter a URL base a partir da requisição
def get_base_url(request: Request) -> str:
    """Retorna a URL base baseada na requisição atual"""
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}"

# Função para converter um caminho de arquivo em URL
def file_path_to_url(file_path):
    if file_path.startswith(SENHA_DIR):
        # É um arquivo de senha
        filename = os.path.basename(file_path)
        return f"/senha/{filename}"
    elif file_path.startswith(GUICHE_DIR):
        # É um arquivo de guichê
        filename = os.path.basename(file_path)
        return f"/guiche/{filename}"
    elif file_path.startswith(CACHE_DIR):
        # É um arquivo de cache regular
        filename = os.path.basename(file_path)
        return f"/audio/{filename}"
    else:
        # Caminho desconhecido
        return file_path

class Texto(BaseModel):
    texto: Optional[str] = None
    language: str = "pt"  # Idioma padrão: português
    reference_file: Optional[str] = None  # Arquivo de referência opcional
    speaker: Optional[str] = None  # Nome do falante pré-definido
    speed: float = 1.0  # Velocidade da fala (0.5 = metade da velocidade, 2.0 = dobro da velocidade)
    force_refresh: bool = False  # Força a regeneração do áudio mesmo que exista no cache
    
    # Parâmetros específicos para chamada de guichê
    senha: Optional[str] = None  # Senha a ser chamada (ex: "Senha 4")
    guiche: Optional[str] = None  # Guichê a ser anunciado (ex: "Guichê 6")
    
    @field_validator('texto')
    @classmethod
    def texto_or_senha_guiche_required(cls, v, info):
        # Se não temos texto, precisamos ter senha e guichê
        if not v and not (info.data.get('senha') and info.data.get('guiche')):
            raise ValueError('Você deve fornecer "texto" OU ambos "senha" e "guiche"')
        return v

@app.get("/")
async def root():
    return {
        "mensagem": "API de síntese de voz TTS",
        "documentacao": "/docs",
        "falantes": "/speakers",
        "cache": "/cache"
    }

@app.get("/speakers")
async def get_speakers():
    """Retorna a lista de falantes disponíveis no modelo."""
    return {"speakers": available_speakers, "default_speakers": DEFAULT_SPEAKERS}

@app.get("/audio-file/{tipo}/{filename}")
async def get_audio_file(tipo: str, filename: str):
    """Serve um arquivo de áudio específico pelo nome do arquivo e tipo"""
    if tipo == "senha":
        file_path = os.path.join(SENHA_DIR, filename)
    elif tipo == "guiche":
        file_path = os.path.join(GUICHE_DIR, filename)
    elif tipo == "texto":
        file_path = os.path.join(CACHE_DIR, filename)
    else:
        raise HTTPException(status_code=400, detail="Tipo de áudio inválido")
    
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    
    # Se não encontrou o arquivo
    raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")

@app.get("/cache")
async def get_cache_info():
    """Retorna informações sobre o cache de áudio"""
    cache_size = 0
    senha_size = 0
    guiche_size = 0
    cache_files = 0
    senha_files = 0
    guiche_files = 0
    
    # Verificar arquivos de texto regular
    for file in os.listdir(CACHE_DIR):
        if file.endswith(".wav"):
            file_path = os.path.join(CACHE_DIR, file)
            cache_size += os.path.getsize(file_path)
            cache_files += 1
    
    # Verificar arquivos de senha
    for file in os.listdir(SENHA_DIR):
        if file.endswith(".wav"):
            file_path = os.path.join(SENHA_DIR, file)
            senha_size += os.path.getsize(file_path)
            senha_files += 1
    
    # Verificar arquivos de guichê
    for file in os.listdir(GUICHE_DIR):
        if file.endswith(".wav"):
            file_path = os.path.join(GUICHE_DIR, file)
            guiche_size += os.path.getsize(file_path)
            guiche_files += 1
    
    total_size = cache_size + senha_size + guiche_size
    total_files = cache_files + senha_files + guiche_files
    
    return {
        "texto_entries": cache_files,
        "texto_size_mb": round(cache_size / (1024 * 1024), 2),
        "senha_entries": senha_files,
        "senha_size_mb": round(senha_size / (1024 * 1024), 2),
        "guiche_entries": guiche_files,
        "guiche_size_mb": round(guiche_size / (1024 * 1024), 2),
        "total_entries": total_files,
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }

@app.delete("/cache")
async def clear_cache():
    """Limpa o cache de áudio"""
    # Limpar cache principal (textos)
    for file in os.listdir(CACHE_DIR):
        if file.endswith(".wav"):
            os.remove(os.path.join(CACHE_DIR, file))
    
    # Limpar cache de senhas
    for file in os.listdir(SENHA_DIR):
        if file.endswith(".wav"):
            os.remove(os.path.join(SENHA_DIR, file))
    
    # Limpar cache de guichês
    for file in os.listdir(GUICHE_DIR):
        if file.endswith(".wav"):
            os.remove(os.path.join(GUICHE_DIR, file))
    
    # Resetar índice de cache
    global cache_index
    cache_index = {}
    save_cache_index()
    
    return {"status": "ok", "message": "Cache limpo com sucesso"}

def generate_cache_key(texto, language, speaker, speed, reference_file=None):
    """Gera uma chave única para o cache com base nos parâmetros"""
    key_parts = [
        texto,
        language,
        str(speaker) if speaker else "None",
        str(speed)
    ]
    
    # Se estiver usando um arquivo de referência, incluir seu conteúdo hash
    if reference_file:
        try:
            with open(reference_file, 'rb') as f:
                reference_hash = hashlib.md5(f.read()).hexdigest()
            key_parts.append(reference_hash)
        except:
            key_parts.append("reference_error")
    
    # Gerar hash MD5 para a chave
    key_string = "_".join(key_parts)
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

@app.post("/falar")
def falar(dados: Texto, request: Request):
    try:
        # Verificar se a velocidade está dentro de limites razoáveis
        speed = max(0.5, min(3.0, dados.speed))  # Limitar entre 0.5 e 3.0
        
        # Determinar o falante a ser usado
        speaker_to_use = None
        
        if dados.speaker:
            # Usar o falante especificado
            speaker_to_use = dados.speaker
        else:
            # Usar o falante padrão para o idioma
            speaker_to_use = DEFAULT_SPEAKERS.get(dados.language, DEFAULT_SPEAKERS["default"])
        
        # URL base para os arquivos de áudio (baseada na requisição atual)
        base_url = get_base_url(request)
        
        # Verificar se é uma chamada de guichê
        if dados.senha and dados.guiche:
            # Verificar se os arquivos já existem antes de gerar
            componentes = {}
            componentes_urls = {}
            
            # 1. Verificar/Gerar arquivo de senha
            senha_safe_name = dados.senha.replace(" ", "_").replace("/", "_").lower()
            senha_file_name = f"{senha_safe_name}_{dados.language}.wav"
            senha_file_path = os.path.join(SENHA_DIR, senha_file_name)
            
            if not os.path.exists(senha_file_path) or dados.force_refresh:
                # Só gera o áudio se não existir ou force_refresh=True
                print(f"Gerando áudio de senha: {dados.senha}")
                tts.tts_to_file(
                    text=dados.senha, 
                    file_path=senha_file_path,
                    speaker=speaker_to_use,
                    language=dados.language,
                    speed=speed
                )
            else:
                print(f"Usando áudio de senha em cache: {senha_file_path}")
                
            componentes["senha"] = senha_file_path
            componentes_urls["senha"] = base_url + f"/senha/{senha_file_name}"
            
            # 2. Verificar/Gerar arquivo de guichê
            guiche_safe_name = dados.guiche.replace(" ", "_").replace("/", "_").lower()
            guiche_file_name = f"{guiche_safe_name}_{dados.language}.wav"
            guiche_file_path = os.path.join(GUICHE_DIR, guiche_file_name)
            
            if not os.path.exists(guiche_file_path) or dados.force_refresh:
                # Só gera o áudio se não existir ou force_refresh=True
                print(f"Gerando áudio de guichê: {dados.guiche}")
                tts.tts_to_file(
                    text=dados.guiche, 
                    file_path=guiche_file_path,
                    speaker=speaker_to_use,
                    language=dados.language,
                    speed=speed
                )
            else:
                print(f"Usando áudio de guichê em cache: {guiche_file_path}")
                
            componentes["guiche"] = guiche_file_path
            componentes_urls["guiche"] = base_url + f"/guiche/{guiche_file_name}"
            
            return {
                "status": "ok",
                "tipo": "guiche",
                "senha": dados.senha,
                "guiche": dados.guiche,
                "componentes": componentes,
                "urls": componentes_urls,
                "language": dados.language,
                "speaker": speaker_to_use,
                "speed": speed
            }
        
        # Para anúncios regulares (não guichê)
        else:
            # Gerar chave de cache
            cache_key = generate_cache_key(
                dados.texto, 
                dados.language, 
                speaker_to_use, 
                speed, 
                dados.reference_file
            )
            
            # Nome do arquivo de cache
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.wav")
            
            # Verificar se já existe no cache
            if os.path.exists(cache_file) and not dados.force_refresh:
                print(f"Usando arquivo em cache: {cache_file}")
                # Registrar no índice de cache para fins estatísticos
                if cache_key not in cache_index:
                    cache_index[cache_key] = {
                        "texto": dados.texto,
                        "language": dados.language,
                        "speaker": speaker_to_use,
                        "speed": speed,
                        "hits": 1,
                        "created": os.path.getctime(cache_file)
                    }
                else:
                    cache_index[cache_key]["hits"] = cache_index[cache_key].get("hits", 0) + 1
                
                save_cache_index()
            else:
                # Gerar novo áudio apenas se não existir ou force_refresh=True
                print(f"Gerando novo áudio para: {dados.texto}")
                
                if dados.reference_file:
                    print(f"Usando arquivo de referência: {dados.reference_file}, velocidade: {speed}")
                    tts.tts_to_file(
                        text=dados.texto, 
                        file_path=cache_file,
                        speaker_wav=dados.reference_file,
                        language=dados.language,
                        speed=speed
                    )
                else:
                    print(f"Usando falante: {speaker_to_use}, velocidade: {speed}")
                    tts.tts_to_file(
                        text=dados.texto, 
                        file_path=cache_file,
                        speaker=speaker_to_use,
                        language=dados.language,
                        speed=speed
                    )
                
                # Registrar no índice de cache
                cache_index[cache_key] = {
                    "texto": dados.texto,
                    "language": dados.language,
                    "speaker": speaker_to_use,
                    "speed": speed,
                    "hits": 1,
                    "created": os.path.getctime(cache_file)
                }
                
                save_cache_index()
            
            # Gerar URL para o arquivo
            cache_url = base_url + file_path_to_url(cache_file)
            
            return {
                "status": "ok", 
                "tipo": "texto",
                "mensagem": dados.texto, 
                "language": dados.language,
                "speaker": speaker_to_use,
                "reference_file": dados.reference_file,
                "speed": speed,
                "cache_file": cache_file,
                "url": cache_url,
                "cached": os.path.exists(cache_file) and not dados.force_refresh
            }
    except Exception as e:
        return {"status": "error", "mensagem": str(e)}
