#!/usr/bin/env python3
"""
Teste do DJNE Scraper
"""
import sys
from datetime import date

print("=" * 60)
print("TESTE DO DJNE SCRAPER")
print("=" * 60)

# Teste de importação
print("\n1. Testando importação...")
try:
    from djne_scraper import buscar_publicacoes_djne
    print("✅ Importação OK")
except Exception as e:
    print(f"❌ Erro na importação: {e}")
    sys.exit(1)

# Teste de dependências
print("\n2. Testando dependências...")
try:
    import requests
    import re
    from bs4 import BeautifulSoup
    print("✅ Dependências OK (requests, re, BeautifulSoup)")
except Exception as e:
    print(f"❌ Erro nas dependências: {e}")
    print("Execute: pip install requests beautifulsoup4")
    sys.exit(1)

# Teste da função
print("\n3. Testando função buscar_publicacoes_djne...")
nome = "EDSON MARCOS FERREIRA PRATTI JUNIOR"
data_teste = date.today()

print(f"   Nome: {nome}")
print(f"   Data: {data_teste}")
print(f"   URL esperada: https://comunica.pje.jus.br/consulta?texto={nome.replace(' ', '%20')}&dataDisponibilizacaoInicio={data_teste}&dataDisponibilizacaoFim={data_teste}")

try:
    publicacoes = buscar_publicacoes_djne(nome, data_teste)
    print(f"\n✅ Função executada com sucesso!")
    print(f"   Total de publicações: {len(publicacoes)}")
    
    if publicacoes:
        print("\n4. Detalhes da primeira publicação:")
        pub = publicacoes[0]
        print(f"   - Processo: {pub.get('process_number', 'N/A')}")
        print(f"   - Órgão: {pub.get('orgao', 'N/A')}")
        print(f"   - Data: {pub.get('data_disponibilizacao', 'N/A')}")
        print(f"   - Tipo: {pub.get('tipo_comunicacao', 'N/A')}")
        print(f"   - Origem: {pub.get('origem', 'N/A')}")
        
        conteudo = pub.get('content', '')
        print(f"   - Tamanho do conteúdo: {len(conteudo)} caracteres")
        print(f"   - Preview: {conteudo[:200]}...")
    else:
        print("\n⚠️ Nenhuma publicação encontrada para a data de hoje")
        print("   Isso pode ser normal se não houver publicações novas")
        
except Exception as e:
    print(f"\n❌ Erro ao executar função: {type(e).__name__}")
    print(f"   Mensagem: {str(e)}")
    import traceback
    print("\n   Traceback completo:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)
