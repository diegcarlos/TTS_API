# TTS API

API de síntese de voz usando o modelo XTTS v2 para chamadas de guichê e texto geral.

## Características

- Suporte para múltiplos idiomas
- Cache inteligente para arquivos de áudio
- Chamada especial para senhas e guichês
- Controle de velocidade da fala
- Escolha de diferentes vozes/falantes

## Instalação

### Usando pip (Recomendado)

1. Clone ou baixe este repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

### Usando Docker

1. Construa a imagem Docker:
   ```
   docker build -t tts-api .
   ```
2. Execute o container:
   ```
   docker run -p 8000:8000 -v $(pwd)/cache_audio:/app/cache_audio tts-api
   ```

## Iniciando o Servidor

Execute o seguinte comando para iniciar o servidor:

```
python run_server.py
```

Por padrão, o servidor será iniciado em `http://localhost:8000`.

Parâmetros opcionais:

- `--host`: Endereço IP para escutar (padrão: `0.0.0.0`)
- `--port`: Porta para escutar (padrão: `8000`)
- `--reload`: Recarregar automaticamente em alterações de código (padrão: `False`)
- `--workers`: Número de workers (padrão: `1`)

## Utilizando a API

### Endpoints Principais

- `GET /`: Página inicial com informações básicas
- `GET /speakers`: Lista de falantes disponíveis no modelo
- `GET /cache`: Informações sobre o cache de áudio
- `DELETE /cache`: Limpa o cache de áudio
- `POST /falar`: Gera fala a partir de texto

### Exemplos de Uso

#### Texto Simples

```python
import requests

url = "http://localhost:8000/falar"
payload = {
    "texto": "Olá, bem-vindo à API de síntese de voz",
    "language": "pt",
    "speed": 1.0
}
response = requests.post(url, json=payload)
print(response.json())
```

#### Chamada de Guichê

```python
import requests

url = "http://localhost:8000/falar"
payload = {
    "senha": "Senha 42",
    "guiche": "Guichê 7",
    "language": "pt",
    "speed": 1.0
}
response = requests.post(url, json=payload)
print(response.json())
```

## Documentação Completa

Acesse a documentação completa da API em:

```
http://localhost:8000/docs
```
