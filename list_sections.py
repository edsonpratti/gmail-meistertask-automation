#!/usr/bin/env python3
"""Script para listar todas as seções de um projeto do MeisterTask"""

import requests
import os

# Carrega configurações
def load_env_var(key):
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    k, v = line.strip().split('=', 1)
                    if k == key:
                        return v
    return None

api_token = load_env_var('MEISTERTASK_API_TOKEN')
project_id = load_env_var('MEISTERTASK_PROJECT_ID')

if not api_token or not project_id:
    print("❌ Erro: MEISTERTASK_API_TOKEN ou MEISTERTASK_PROJECT_ID não encontrados no .env")
    exit(1)

# Lista todas as seções do projeto
url = f"https://www.meistertask.com/api/projects/{project_id}/sections"
headers = {"Authorization": f"Bearer {api_token}"}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    sections = response.json()
    
    print(f"\n📋 Seções do Projeto (ID: {project_id}):\n")
    print(f"{'ID':<15} {'Nome':<30}")
    print("-" * 45)
    
    for section in sections:
        section_id = section.get('id', 'N/A')
        section_name = section.get('name', 'Sem nome')
        print(f"{section_id:<15} {section_name:<30}")
    
    print("\n💡 Copie o ID da seção 'Publicações' e atualize MEISTERTASK_SECTION_ID no arquivo .env")
    
except Exception as e:
    print(f"❌ Erro ao buscar seções: {e}")
