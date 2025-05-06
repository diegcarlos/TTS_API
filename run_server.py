import uvicorn
import argparse

if __name__ == "__main__":
    # Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description="Servidor de API TTS")
    parser.add_argument("--host", type=str, default="0.0.0.0", 
                        help="Endereço IP para escutar (0.0.0.0 para todas as interfaces)")
    parser.add_argument("--port", type=int, default=8000, 
                        help="Porta para escutar")
    parser.add_argument("--reload", action="store_true", 
                        help="Recarregar automaticamente em alterações de código")
    parser.add_argument("--workers", type=int, default=1, 
                        help="Número de workers (1 é recomendado para aplicações com GPU)")
    
    args = parser.parse_args()
    
    # Imprimir informações sobre como acessar a API
    print(f"\nIniciando servidor TTS API:")
    print(f"- URL local: http://localhost:{args.port}")
    
    # Tentar obter endereço IP externo para facilitar o acesso de outras máquinas
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"- URL da rede local: http://{local_ip}:{args.port}")
    except:
        print("- Não foi possível determinar o IP local")
        
    print("\nPara acessar os endpoints:")
    print(f"- Documentação: http://localhost:{args.port}/docs")
    print(f"- Lista de falantes: http://localhost:{args.port}/speakers")
    print(f"- Status do cache: http://localhost:{args.port}/cache")
    print("\nPara parar o servidor: CTRL+C\n")
    
    # Iniciar o servidor
    uvicorn.run(
        "main:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload,
        workers=args.workers
    ) 