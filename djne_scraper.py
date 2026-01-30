#!/usr/bin/env python3
"""
DJNE Scraper - Busca publicações no Diário de Justiça Eletrônico Nacional
Usa requests com headers de browser para acessar API
"""
import re
import requests
from datetime import datetime, date
import json


def buscar_publicacoes_djne(nome_advogado, data_inicio, data_fim=None):
    """
    Busca publicações no DJNE para um advogado em uma data específica
    
    Args:
        nome_advogado (str): Nome completo do advogado em maiúsculas
        data_inicio (date ou str): Data inicial da busca (formato YYYY-MM-DD ou objeto date)
        data_fim (date ou str, opcional): Data final da busca. Se não informado, usa data_inicio
    
    Returns:
        list: Lista de dicionários com as publicações encontradas
    """
    
    # Converte datas para string no formato YYYY-MM-DD
    if isinstance(data_inicio, date):
        data_inicio_str = data_inicio.strftime('%Y-%m-%d')
    else:
        data_inicio_str = data_inicio
    
    if data_fim is None:
        data_fim_str = data_inicio_str
    elif isinstance(data_fim, date):
        data_fim_str = data_fim.strftime('%Y-%m-%d')
    else:
        data_fim_str = data_fim
    
    # Monta a URL da consulta
    url = f"https://comunica.pje.jus.br/consulta?texto={nome_advogado.replace(' ', '%20')}&dataDisponibilizacaoInicio={data_inicio_str}&dataDisponibilizacaoFim={data_fim_str}"
    
    # Headers simulando um browser real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Cria uma sessão para manter cookies
        session = requests.Session()
        
        # Primeira requisição - carrega a página
        print(f"DEBUG: Acessando URL: {url}")
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"DEBUG: Resposta HTTP: {response.status_code}")
        
        # Tenta acessar a API diretamente (o site usa uma API JSON)
        # URL da API baseada na análise do site
        api_url = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
        
        params = {
            'texto': nome_advogado,
            'dataDisponibilizacaoInicio': data_inicio_str,
            'dataDisponibilizacaoFim': data_fim_str,
            'tamanho': 100,  # máximo de resultados
            'pagina': 0
        }
        
        print(f"DEBUG: Chamando API: {api_url}")
        print(f"DEBUG: Parâmetros: {params}")
        api_response = session.get(api_url, params=params, headers=headers, timeout=30)
        print(f"DEBUG: API Response Status: {api_response.status_code}")
        
        publicacoes = []
        
        if api_response.status_code == 200:
            try:
                data = api_response.json()
                print(f"DEBUG: JSON recebido, tipo: {type(data)}")
                
                # A API retorna JSON com lista de comunicações
                if isinstance(data, dict):
                    comunicacoes = data.get('items', []) or data.get('content', []) or data.get('data', [])
                    total = data.get('total', len(comunicacoes))
                    print(f"DEBUG: Encontradas {len(comunicacoes)} comunicações (total: {total})")
                else:
                    comunicacoes = []
                    print(f"DEBUG: Resposta não é dict, é {type(data)}")
                
                for com in comunicacoes:
                    numero_processo = com.get('numeroprocessocommascara') or com.get('numero_processo') or com.get('numeroProcesso') or 'Não identificado'
                    
                    publicacao = {
                        'process_number': numero_processo,
                        'orgao': com.get('nomeOrgao') or com.get('orgao') or 'Não identificado',
                        'data_disponibilizacao': com.get('datadisponibilizacao') or com.get('data_disponibilizacao') or com.get('dataDisponibilizacao') or '',
                        'tipo_comunicacao': com.get('tipoComunicacao') or com.get('tipo_comunicacao') or 'Intimação',
                        'content': com.get('texto') or com.get('conteudo') or com.get('content') or '',
                        'source_subject': f"DJNE - {numero_processo}",
                        'origem': 'DJNE'
                    }
                    
                    print(f"DEBUG: Publicação extraída - Processo: {numero_processo}")
                    publicacoes.append(publicacao)
                
                print(f"DEBUG: Total de publicações extraídas da API: {len(publicacoes)}")
                return publicacoes
                
            except json.JSONDecodeError as e:
                # API não retornou JSON, tenta fazer scraping do HTML
                print(f"DEBUG: Erro ao decodificar JSON: {e}")
                print(f"DEBUG: Conteúdo da resposta (primeiros 500 chars): {api_response.text[:500]}")
                pass
        else:
            print(f"DEBUG: API retornou status {api_response.status_code}, tentando scraping HTML")
        
        # Fallback: scraping do HTML se API não funcionou
        print("DEBUG: Usando fallback de scraping HTML...")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        texto_completo = soup.get_text(separator='\n')
        print(f"DEBUG: HTML convertido para texto, tamanho: {len(texto_completo)} caracteres")
        
        # Procura pelo padrão "Processo XXXX"
        processo_pattern = r'Processo\s+(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
        
        # Encontra todos os processos
        matches = list(re.finditer(processo_pattern, texto_completo, re.IGNORECASE))
        print(f"DEBUG: Encontrados {len(matches)} processos no HTML")
        
        if not matches:
            # Não encontrou publicações
            print("DEBUG: Nenhuma publicação encontrada")
            return []
        
        # Para cada processo encontrado, extrai o bloco de conteúdo
        for i, match in enumerate(matches):
            numero_processo = match.group(1)
            
            # Início do conteúdo (logo após o número do processo)
            inicio = match.end()
            
            # Fim do conteúdo (início do próximo processo ou fim do texto)
            if i + 1 < len(matches):
                fim = matches[i + 1].start()
            else:
                fim = len(texto_completo)
            
            # Extrai o bloco de conteúdo desta publicação
            bloco_conteudo = texto_completo[inicio:fim].strip()
            
            # Extrai informações específicas
            orgao_match = re.search(r'Órgão:\s*([^\n]+)', bloco_conteudo)
            data_match = re.search(r'Data de disponibilização:\s*(\d{2}/\d{2}/\d{4})', bloco_conteudo)
            tipo_match = re.search(r'Tipo de comunicação:\s*([^\n]+)', bloco_conteudo)
            
            # Monta a publicação
            publicacao = {
                'process_number': numero_processo,
                'orgao': orgao_match.group(1).strip() if orgao_match else 'Não identificado',
                'data_disponibilizacao': data_match.group(1) if data_match else '',
                'tipo_comunicacao': tipo_match.group(1).strip() if tipo_match else 'Intimação',
                'content': bloco_conteudo[:5000],  # Limita a 5000 caracteres
                'source_subject': f"DJNE - {numero_processo}",
                'origem': 'DJNE'
            }
            
            publicacoes.append(publicacao)
        
        print(f"DEBUG: Total de publicações extraídas do HTML: {len(publicacoes)}")
        return publicacoes
        
    except Exception as e:
        print(f"DEBUG: Exceção capturada: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Erro ao processar publicações do DJNE: {str(e)}")


def contar_publicacoes_djne(nome_advogado, data_inicio, data_fim=None):
    """
    Conta quantas publicações existem no DJNE sem fazer parsing completo
    
    Args:
        nome_advogado (str): Nome completo do advogado
        data_inicio (date ou str): Data inicial
        data_fim (date ou str, opcional): Data final
    
    Returns:
        int: Número de publicações encontradas
    """
    try:
        publicacoes = buscar_publicacoes_djne(nome_advogado, data_inicio, data_fim)
        return len(publicacoes)
    except:
        return 0


if __name__ == "__main__":
    # Teste
    from datetime import date
    
    nome = "EDSON MARCOS FERREIRA PRATTI JUNIOR"
    data = date.today()
    
    print(f"Buscando publicações para {nome} em {data}...")
    
    try:
        pubs = buscar_publicacoes_djne(nome, data)
        print(f"\n✅ Encontradas {len(pubs)} publicações:")
        
        for idx, pub in enumerate(pubs, 1):
            print(f"\n{idx}. Processo: {pub['process_number']}")
            print(f"   Órgão: {pub['orgao']}")
            print(f"   Data: {pub['data_disponibilizacao']}")
            print(f"   Tipo: {pub['tipo_comunicacao']}")
            print(f"   Conteúdo (primeiros 200 chars): {pub['content'][:200]}...")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
