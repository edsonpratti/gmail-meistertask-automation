#!/usr/bin/env python3
import re

email_real = """
Recorte Digital - OAB - Resultado da Busca

Publicação: 1     

Data de Disponibilização: 22/01/2026
Data de Publicação: 23/01/2026
Jornal: Diário da Justiça Eletrônico do Estado do Rio de Janeiro
Caderno: TJRJDJEN
Página: 55434

Publicação: Intimacao

PROCESSO: 0028066-08.2021.8.19.0209 - PROCEDIMENTO COMUM CiVEL
POLO ATIVO: ALESSANDRA RODRIGUES DE SOUSA 
POLO PASSIVO: ELETRONICA JM 3939


Publicação: 2     

Data de Disponibilização: 22/01/2026
Data de Publicação: 23/01/2026
Jornal: Diário da Justiça Eletrônico

Publicação: Intimacao

PROCESSO: 0000702-21.2017.8.19.0203 - USUCAPIaO
POLO ATIVO: ROMILDO IDAMAR COUTO


Publicação: 3     

Data de Disponibilização: 22/01/2026
Data de Publicação: 23/01/2026

Publicação: Intimacao

PROCESSO: 0099510-52.1998.8.19.0001 - SEPARAcaO CONSENSUAL

Total de Publicações: 3
"""

print("="*70)
print("TESTANDO PADRÕES NO EMAIL REAL")
print("="*70)

# Teste 1: Buscar "Publicação: \d+"
print("\n1. Buscando 'Publicação: \\d+'")
pattern1 = r'Publicação:\s*\d+'
matches1 = list(re.finditer(pattern1, email_real, re.IGNORECASE))
print(f"   Encontrados: {len(matches1)} matches")
for i, m in enumerate(matches1, 1):
    context = email_real[m.start():m.end()+50]
    print(f"   {i}. '{context[:40]}...'")

# Teste 2: Buscar "Publicação: \d+\s+" (com espaços após o número)
print("\n2. Buscando 'Publicação: \\d+\\s+' (com espaços)")
pattern2 = r'Publicação:\s*\d+\s+'
matches2 = list(re.finditer(pattern2, email_real, re.IGNORECASE))
print(f"   Encontrados: {len(matches2)} matches")
for i, m in enumerate(matches2, 1):
    context = email_real[m.start():m.end()+50]
    print(f"   {i}. '{context[:40]}...'")

# Teste 3: Buscar por PROCESSO:
print("\n3. Buscando 'PROCESSO:'")
pattern3 = r'PROCESSO:\s*(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
matches3 = list(re.finditer(pattern3, email_real, re.IGNORECASE))
print(f"   Encontrados: {len(matches3)} processos")
for i, m in enumerate(matches3, 1):
    print(f"   {i}. {m.group(1)}")

# Teste 4: Extração usando "Publicação: \d+\s+" como separador
print("\n4. EXTRAÇÃO USANDO PADRÃO CORRETO")
print("-"*70)
pattern = r'Publicação:\s*\d+\s+'
pub_matches = list(re.finditer(pattern, email_real, re.IGNORECASE))

publications = []
for i, match in enumerate(pub_matches):
    start_pos = match.start()
    end_pos = pub_matches[i + 1].start() if i + 1 < len(pub_matches) else len(email_real)
    
    pub_content = email_real[start_pos:end_pos].strip()
    
    # Extrai processo
    process_pattern = r'PROCESSO:\s*(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
    process_match = re.search(process_pattern, pub_content, re.IGNORECASE)
    process_number = process_match.group(1) if process_match else f'Pub {i+1}'
    
    publications.append({
        'number': process_number,
        'content_size': len(pub_content)
    })
    
    print(f"\nPublicação {i+1}:")
    print(f"  Processo: {process_number}")
    print(f"  Tamanho: {len(pub_content)} chars")
    print(f"  Preview: {pub_content[:100]}...")

print(f"\n{'='*70}")
print(f"TOTAL: {len(publications)} publicações extraídas")
print(f"{'='*70}")
