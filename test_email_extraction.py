#!/usr/bin/env python3
"""
Teste da função de extração de publicações de emails
"""
import re

def extract_publications_from_email(email_body, email_subject):
    """
    Extrai múltiplas publicações de processos judiciais de um email
    Testa múltiplos padrões para encontrar as separações
    """
    publications = []
    
    # Testa vários padrões possíveis em ordem de especificidade
    patterns_to_try = [
        # Padrões específicos primeiro
        (r'Publicação\s*n[º°]\s*\d+[:\.\s]*', 'Publicação nº N'),
        (r'Publicação:\s*\d+\.\s+', 'Publicação: N.'),
        (r'Publicação\s+\d+\s*[-:\.]\s*', 'Publicação N -'),
        (r'Publicação:\s*\d+', 'Publicação: N'),
        (r'\n\d+\.\s*Processo\s+n', 'N. Processo n'),  # Padrão numerado
        (r'\n\d+\s*[-\.]\s*Processo\s+', 'N - Processo'),
        (r'Processo\s+n[º°]\s*\d{7}', 'Processo nº'),  # Inicio direto com processo
        (r'Publicação:', 'Publicação: (genérico)')
    ]
    
    pub_matches = None
    pattern_used = None
    
    for pattern, description in patterns_to_try:
        matches = list(re.finditer(pattern, email_body, re.IGNORECASE))
        if matches and len(matches) > 0:
            pub_matches = matches
            pattern_used = description
            print(f"✓ Usando padrão: {description} - Encontradas {len(matches)} ocorrências")
            break
    
    if not pub_matches or len(pub_matches) == 0:
        # Tenta encontrar pelo menos um processo
        process_pattern = r'\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4}'
        process_matches = list(re.finditer(process_pattern, email_body))
        
        if process_matches:
            print(f"✓ Encontrados {len(process_matches)} processos sem marcadores de publicação")
            # Encontrou processos, mas sem marcadores claros de separação
            # Trata cada processo como uma publicação separada
            for match in process_matches:
                process_number = match.group(0)
                # Pega contexto ao redor do processo (500 chars antes e depois)
                start = max(0, match.start() - 500)
                end = min(len(email_body), match.end() + 1500)
                pub_content = email_body[start:end].strip()
                
                publications.append({
                    'process_number': process_number,
                    'content': pub_content,
                    'source_subject': email_subject
                })
        else:
            print("⚠ Nenhum processo encontrado, tratando email inteiro como publicação")
            # Não encontrou nada, trata o email inteiro como uma publicação
            publications.append({
                'process_number': 'Sem número identificado',
                'content': email_body[:5000],
                'source_subject': email_subject
            })
        
        return publications
    
    # Para cada match, extrai o bloco completo
    for i, match in enumerate(pub_matches):
        # Início da publicação
        start_pos = match.start()
        
        # Fim da publicação (início da próxima ou fim do texto)
        end_pos = pub_matches[i + 1].start() if i + 1 < len(pub_matches) else len(email_body)
        
        # Extrai o conteúdo completo da publicação
        pub_content = email_body[start_pos:end_pos].strip()
        
        # Tenta extrair número do processo (padrão brasileiro - corrigido)
        # Formato: NNNNNNN-NN.AAAA.N.NN.NNNN (onde N pode ter múltiplos dígitos)
        process_pattern = r'(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
        process_match = re.search(process_pattern, pub_content)
        process_number = process_match.group(0) if process_match else f'Publicação {i+1}'
        
        publications.append({
            'process_number': process_number,
            'content': pub_content,
            'source_subject': email_subject
        })
    
    return publications


# Casos de teste
print("="*70)
print("TESTE DE EXTRAÇÃO DE PUBLICAÇÕES DE EMAILS")
print("="*70)

# Caso 1: Email com "Publicação: N"
print("\n\n📧 CASO 1: Email com padrão 'Publicação: N'")
print("-"*70)
email1 = """
Intimações do dia 23/01/2026

Publicação: 1
Processo nº 1234567-89.2025.8.26.0100
Tribunal de Justiça de São Paulo
Autor: João da Silva vs Réu: Maria Santos
Fica o autor intimado para comparecer...

Publicação: 2
Processo nº 7654321-98.2025.8.26.0200
Tribunal de Justiça de São Paulo
Autor: Pedro Oliveira vs Réu: Ana Costa
Fica o réu intimado para apresentar...
"""
pubs1 = extract_publications_from_email(email1, "Intimações TJSP")
print(f"\n✅ Resultado: {len(pubs1)} publicações encontradas")
for i, pub in enumerate(pubs1, 1):
    print(f"  {i}. Processo: {pub['process_number']}")

# Caso 2: Email com numeração simples
print("\n\n📧 CASO 2: Email com numeração simples")
print("-"*70)
email2 = """
1. Processo nº 1111111-11.2025.8.26.0300
Intimação para audiência...

2. Processo nº 2222222-22.2025.8.26.0400
Intimação para juntada...

3. Processo nº 3333333-33.2025.8.26.0500
Intimação para manifestação...
"""
pubs2 = extract_publications_from_email(email2, "DJSP - Intimações")
print(f"\n✅ Resultado: {len(pubs2)} publicações encontradas")
for i, pub in enumerate(pubs2, 1):
    print(f"  {i}. Processo: {pub['process_number']}")

# Caso 3: Email sem marcadores claros
print("\n\n📧 CASO 3: Email sem marcadores (apenas processos)")
print("-"*70)
email3 = """
Diário da Justiça - 23/01/2026

Processo nº 9876543-21.2025.8.26.0100
Vistos. Defiro o pedido de prazo...

Processo nº 5555555-55.2025.8.26.0200
Indefiro o pedido liminar...
"""
pubs3 = extract_publications_from_email(email3, "DJ - Publicações")
print(f"\n✅ Resultado: {len(pubs3)} publicações encontradas")
for i, pub in enumerate(pubs3, 1):
    print(f"  {i}. Processo: {pub['process_number']}")
    print(f"      Conteúdo: {pub['content'][:80]}...")

# Caso 4: Email com "Publicação nº"
print("\n\n📧 CASO 4: Email com padrão 'Publicação nº'")
print("-"*70)
email4 = """
Publicações do Tribunal

Publicação nº 1: Processo nº 1234567-89.2025.4.03.6100
Despacho: Intime-se...

Publicação nº 2: Processo nº 7777777-77.2025.4.03.6100
Decisão: Defiro...
"""
pubs4 = extract_publications_from_email(email4, "TRF3 - Intimações")
print(f"\n✅ Resultado: {len(pubs4)} publicações encontradas")
for i, pub in enumerate(pubs4, 1):
    print(f"  {i}. Processo: {pub['process_number']}")

# Caso 5: Email do Recorte Digital OAB/RJ (caso real do usuário)
print("\n\n📧 CASO 5: Email Recorte Digital OAB/RJ (caso real)")
print("-"*70)
email5 = """
Recorte Digital - OAB - Resultado da Busca

Publicação: 1     

Data de Disponibilização: 22/01/2026
Data de Publicação: 23/01/2026
Jornal: Diário da Justiça Eletrônico do Estado do Rio de Janeiro

Publicação: Intimacao

PROCESSO: 0028066-08.2021.8.19.0209 - PROCEDIMENTO COMUM CiVEL
POLO ATIVO: ALESSANDRA RODRIGUES DE SOUSA 
POLO PASSIVO: ELETRONICA JM 3939 COMERCIO E ASSITENCIA TECNICA EIRELI


Publicação: 2     

Data de Disponibilização: 22/01/2026
Data de Publicação: 23/01/2026

Publicação: Intimacao

PROCESSO: 0000702-21.2017.8.19.0203 - USUCAPIaO
POLO ATIVO: ROMILDO IDAMAR COUTO 
POLO ATIVO: ROSENLDA COUTO XAVIER


Publicação: 3     

Data de Disponibilização: 22/01/2026
Data de Publicação: 23/01/2026

Publicação: Intimacao

PROCESSO: 0099510-52.1998.8.19.0001 - SEPARAcaO CONSENSUAL
POLO ATIVO: PROCESSO ESTA EM SEGREDO DE JUSTICA
"""
pubs5 = extract_publications_from_email(email5, "Recorte Digital OAB/RJ")
print(f"\n✅ Resultado: {len(pubs5)} publicações encontradas")
for i, pub in enumerate(pubs5, 1):
    print(f"  {i}. Processo: {pub['process_number']}")
    print(f"      Tamanho do conteúdo: {len(pub['content'])} chars")

# Caso 6: Email sem nenhum processo
print("\n\n📧 CASO 6: Email sem processos identificáveis")
print("-"*70)
email6 = """
Este é um email genérico sobre uma reunião
agendada para amanhã às 10h.
"""
pubs6 = extract_publications_from_email(email6, "Reunião")
print(f"\n✅ Resultado: {len(pubs6)} publicações encontradas")
for i, pub in enumerate(pubs6, 1):
    print(f"  {i}. Processo: {pub['process_number']}")

print("\n" + "="*70)
print("TESTES CONCLUÍDOS")
print("="*70)
