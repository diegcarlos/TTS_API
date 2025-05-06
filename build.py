#!/usr/bin/env python3
import os
import shutil
import subprocess
import zipfile
import argparse

def main():
    parser = argparse.ArgumentParser(description="Construir um pacote de distribuição para a TTS_API")
    parser.add_argument("--output", type=str, default="dist", help="Diretório de saída para o pacote")
    args = parser.parse_args()
    
    # Crie o diretório de saída se não existir
    output_dir = args.output
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # Arquivos e pastas para incluir no pacote
    files_to_include = [
        "main.py",
        "run_server.py",
        "requirements.txt",
        "README.md",
        "Dockerfile"
    ]
    
    # Diretórios para incluir (recursivamente)
    dirs_to_include = [
        "cache_audio"
    ]
    
    # Copiar arquivos para o diretório de saída
    for file in files_to_include:
        if os.path.exists(file):
            shutil.copy(file, os.path.join(output_dir, file))
    
    # Copiar diretórios recursivamente
    for dir_name in dirs_to_include:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join(output_dir, dir_name))
        else:
            # Criar diretórios vazios se não existirem
            os.makedirs(os.path.join(output_dir, dir_name))
            if dir_name == "cache_audio":
                os.makedirs(os.path.join(output_dir, dir_name, "senha"))
                os.makedirs(os.path.join(output_dir, dir_name, "guiche"))
    
    # Criar arquivo de inicialização simples
    with open(os.path.join(output_dir, "start_server.sh"), "w") as f:
        f.write("#!/bin/bash\n")
        f.write("echo \"Instalando dependências...\"\n")
        f.write("pip install -r requirements.txt\n")
        f.write("echo \"Iniciando servidor TTS...\"\n")
        f.write("python run_server.py\n")
    
    # Tornar o script de inicialização executável
    os.chmod(os.path.join(output_dir, "start_server.sh"), 0o755)
    
    # Criar arquivo de inicialização para Windows
    with open(os.path.join(output_dir, "start_server.bat"), "w") as f:
        f.write("@echo off\n")
        f.write("echo Instalando dependencias...\n")
        f.write("pip install -r requirements.txt\n")
        f.write("echo Iniciando servidor TTS...\n")
        f.write("python run_server.py\n")
        f.write("pause\n")
    
    # Criar um arquivo ZIP com tudo
    zip_filename = f"{output_dir}/tts_api.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Adicionar todos os arquivos do diretório de saída ao ZIP
        for root, _, files in os.walk(output_dir):
            for file in files:
                if file == "tts_api.zip":  # Não incluir o próprio arquivo ZIP
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_dir))
    
    print(f"Pacote criado em {zip_filename}")
    print(f"Arquivos extraídos em {output_dir}")
    print("\nPara iniciar o servidor, execute:")
    print("  - Em Linux/Mac: ./start_server.sh")
    print("  - Em Windows: start_server.bat")

if __name__ == "__main__":
    main() 