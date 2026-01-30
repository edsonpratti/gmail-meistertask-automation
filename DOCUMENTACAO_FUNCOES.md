# 📧 Documentação: Sistema de Leitura de Emails e Criação de Tarefas no MeisterTask

**Data:** 22 de janeiro de 2026  
**Sistema:** Automação Gmail → MeisterTask

---

## 📋 Visão Geral

O sistema automatiza o processo de leitura de emails do Gmail contendo publicações judiciais e criação de tarefas correspondentes no MeisterTask, com validação manual em múltiplas etapas.

---

## 🔄 Fluxo Completo do Processo

```
1. Usuário define FILTROS (texto, data, status)
   ↓
2. Sistema busca EMAILS no Gmail
   ↓
3. Usuário SELECIONA quais emails processar
   ↓
4. Sistema EXTRAI PUBLICAÇÕES de cada email
   ↓
5. Para cada publicação:
   - Identifica número do processo
   - Extrai partes envolvidas
   - Monta conteúdo completo
   ↓
6. Usuário VALIDA publicações extraídas
   ↓
7. Sistema CRIA TAREFAS no MeisterTask
   - Título: [processo] - [partes]
   - Descrição: conteúdo completo
   ↓
8. Exibe RELATÓRIO de sucessos/erros
```

---

## 🔧 Funções Principais

### 1️⃣ LEITURA E FILTRAGEM DE EMAILS

**Função:** `search_emails(service, filters)`  
**Localização:** [dashboard.py](dashboard.py#L123-L196)

#### O que faz:
- Conecta à API do Gmail usando credenciais OAuth2
- Filtra emails por critérios definidos pelo usuário
- Retorna lista de emails processados

#### Filtros disponíveis:
- **Texto:** Busca no assunto OU no corpo do email
- **Data:** Período específico (data inicial e final)
- **Status:** Lido / Não lido / Todos

#### Construção da Query:
```python
# Exemplo de query construída
query_parts = []

# Filtro de texto
if filters.get('text_search'):
    query_parts.append(f'(subject:{texto} OR {texto})')

# Filtro de data
if filters.get('date_from'):
    adjusted_date = date_from - timedelta(days=1)
    query_parts.append(f'after:{adjusted_date.strftime("%Y/%m/%d")}')

if filters.get('date_to'):
    adjusted_date = date_to + timedelta(days=1)
    query_parts.append(f'before:{adjusted_date.strftime("%Y/%m/%d")}')

# Filtro de status
if filters.get('read_status') == 'unread':
    query_parts.append('is:unread')

# Query final
query = ' '.join(query_parts)
```

#### Retorno:
Lista de dicionários com estrutura:
```python
{
    'id': 'msg_id_123456',
    'subject': 'Assunto do email',
    'sender': 'remetente@exemplo.com',
    'date': 'Thu, 22 Jan 2026 10:30:00',
    'body': 'Conteúdo completo do email...',
    'is_read': False,
    'raw_data': {...}  # Dados brutos da API do Gmail
}
```

#### Limitações:
- Máximo de 50 emails por busca
- Requer arquivo `credentials.json` e `token.pickle` configurados

---

### 2️⃣ EXTRAÇÃO DO CORPO DO EMAIL

**Função:** `extract_email_body(message)`  
**Localização:** [dashboard.py](dashboard.py#L198-L241)

#### O que faz:
- Decodifica o conteúdo base64 do email
- Converte HTML para texto plano quando necessário
- Preserva formatação e links importantes

#### Tratamento de formatos:
1. **Emails multipart:** Processa cada parte separadamente
2. **text/plain:** Prioriza texto plano (quando disponível)
3. **text/html:** Converte para texto usando biblioteca `html2text`
4. **Fallback:** Retorna mensagem de erro se não conseguir extrair

#### Configuração do html2text:
```python
h = html2text.HTML2Text()
h.ignore_links = False      # Preserva links
h.ignore_images = True      # Remove imagens
h.ignore_emphasis = False   # Preserva negrito/itálico
h.body_width = 0            # Sem quebra automática de linha
```

#### Exemplo de processamento:
```
Entrada (HTML):
<html><body><p><strong>PROCESSO:</strong> 1234567-12.2024.1.23.4567</p></body></html>

Saída (Texto):
**PROCESSO:** 1234567-12.2024.1.23.4567
```

---

### 3️⃣ EXTRAÇÃO DE PUBLICAÇÕES JUDICIAIS

**Função:** `extract_publications_from_email(email_body, email_subject)`  
**Localização:** [dashboard.py](dashboard.py#L243-L302)

#### O que faz:
- **Divide** um email em múltiplas publicações
- **Identifica** separadores usando regex
- **Extrai** número do processo de cada publicação
- **Associa** conteúdo ao assunto do email de origem

#### Padrões de separação testados (em ordem):
1. `Publicação:\s*\d+\.\s+` → Publicação: N. (com ponto e espaços)
2. `Publicação:\s*\d+\.` → Publicação: N. (com ponto)
3. `Publicação:\s*\d+` → Publicação: N (sem ponto)
4. `Publicação:` → Publicação: (genérico)

#### Extração do número do processo:
```python
# Padrão de processo judicial brasileiro
process_pattern = r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})'
# Exemplo: 1234567-12.2024.1.23.4567
```

#### Exemplo de processamento:
```
Email recebido:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Publicação: 1. 
Processo: 1234567-12.2024.1.23.4567
REQUERENTE: João da Silva
REQUERIDO: Empresa XYZ
[conteúdo da publicação 1]

Publicação: 2.
Processo: 7654321-98.2024.1.23.9876
AUTOR: Maria Santos
RÉU: Banco ABC
[conteúdo da publicação 2]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Resultado:
[
    {
        'process_number': '1234567-12.2024.1.23.4567',
        'content': 'Publicação: 1. Processo: 1234567-12...',
        'source_subject': 'Assunto do email'
    },
    {
        'process_number': '7654321-98.2024.1.23.9876',
        'content': 'Publicação: 2. Processo: 7654321-98...',
        'source_subject': 'Assunto do email'
    }
]
```

#### Comportamento especial:
- Se **nenhum padrão** for encontrado, trata o email inteiro como uma única publicação
- Limita conteúdo a 5000 caracteres por publicação

---

### 4️⃣ EXTRAÇÃO DE PARTES DO PROCESSO

**Função:** `extract_parties_from_publication(pub_content)`  
**Localização:** [dashboard.py](dashboard.py#L304-L390)

#### O que faz:
- Identifica **nomes das partes** envolvidas no processo
- Usa múltiplos padrões regex para diferentes tipos de ações
- Remove informações desnecessárias (CPF/CNPJ)
- Formata resultado padronizado

#### Padrões suportados:
1. `REQUERENTE: NOME vs REQUERIDO: NOME`
2. `EXEQUENTE: NOME vs EXECUTADO: NOME`
3. `AUTOR: NOME vs RÉU: NOME`
4. `APELANTE: NOME vs APELADO: NOME`
5. `RECORRENTE: NOME vs RECORRIDO: NOME`
6. `EMBARGANTE: NOME vs EMBARGADO: NOME`
7. `AGRAVANTE: NOME vs AGRAVADO: NOME`
8. `IMPETRANTE: NOME vs IMPETRADO: NOME`
9. `CONSULENTE: NOME vs CONSULADO: NOME`
10. `POLO ATIVO: NOME vs POLO PASSIVO: NOME`
11. Padrões genéricos de partes

#### Processamento:
```python
# 1. Busca padrão no conteúdo
match = re.search(pattern, pub_content, re.IGNORECASE | re.DOTALL)

# 2. Extrai nomes das partes
party1 = match.group(1).strip()
party2 = match.group(2).strip()

# 3. Remove CPF/CNPJ
party1 = re.sub(r'\d{11,}', '', party1).strip()
party2 = re.sub(r'\d{11,}', '', party2).strip()

# 4. Limita tamanho (máx 50 caracteres)
if len(party1) > 50:
    party1 = party1[:50].strip()

# 5. Formata resultado
parties = f"{party1} x {party2}"
```

#### Exemplos de saída:
```
"JOÃO DA SILVA x EMPRESA XYZ LTDA"
"MARIA SANTOS OLIVEIRA x BANCO ABC S.A."
"Partes não identificadas"  # Quando não encontra padrão
```

---

### 5️⃣ CRIAÇÃO DE TAREFAS NO MEISTERTASK

**Função:** `create_meistertask_task(process_number, parties, description, section_id, api_token)`  
**Localização:** [dashboard.py](dashboard.py#L392-L427)

#### O que faz:
- Cria tarefa na API do MeisterTask
- Monta título formatado
- Adiciona descrição completa
- Retorna status de sucesso/erro

#### Requisição HTTP:
```http
POST https://www.meistertask.com/api/sections/{section_id}/tasks
Headers:
    Authorization: Bearer {api_token}
    Content-Type: application/json
    
Body:
{
    "name": "1234567-12.2024.1.23.4567 - JOÃO DA SILVA x EMPRESA XYZ",
    "notes": "[Conteúdo completo da publicação judicial...]"
}
```

#### Montagem do título:
```python
# Formato: [número processo] - [partes]
title = f"{process_number} - {parties}"

# Limitação da API do MeisterTask
if len(title) > 250:
    title = title[:247] + "..."
```

#### Retorno da função:
```python
# Sucesso (status 200 ou 201)
return True, {
    'id': 'task_id_123',
    'name': 'Título da tarefa',
    'created_at': '2026-01-22T10:30:00Z',
    ...
}

# Erro
return False, "Status 400: Invalid section_id"
```

#### Tratamento de erros:
- Timeout de 30 segundos
- Captura exceções de conexão
- Retorna mensagem detalhada de erro

---

## 📊 Funcionalidades Adicionais

### Gerenciamento de Duplicatas

#### 1. Listar Tarefas Existentes
**Função:** `list_meistertask_tasks(section_id, api_token)`  
**Localização:** [dashboard.py](dashboard.py#L429-L451)

```http
GET https://www.meistertask.com/api/sections/{section_id}/tasks
```

Retorna todas as tarefas de uma seção específica.

---

#### 2. Identificar Duplicatas
**Função:** `find_duplicate_tasks(tasks)`  
**Localização:** [dashboard.py](dashboard.py#L492-L509)

```python
# Agrupa tarefas por número de processo
process_dict = {}
for task in tasks:
    process_number = extract_process_number(task['name'])
    if process_number:
        process_dict[process_number].append(task)

# Retorna apenas processos com múltiplas tarefas
duplicates = {k: v for k, v in process_dict.items() if len(v) > 1}
```

**Exemplo de saída:**
```python
{
    '1234567-12.2024.1.23.4567': [
        {'id': 'task1', 'name': '1234567-12... - JOÃO x EMPRESA'},
        {'id': 'task2', 'name': '1234567-12... - JOÃO x EMPRESA'},
        {'id': 'task3', 'name': '1234567-12... - JOÃO x EMPRESA'}
    ]
}
```

---

#### 3. Deletar Tarefas
**Função:** `delete_meistertask_task(task_id, api_token)`  
**Localização:** [dashboard.py](dashboard.py#L453-L476)

```http
DELETE https://www.meistertask.com/api/tasks/{task_id}
```

Retorna sucesso (status 200/204) ou mensagem de erro.

---

#### 4. Extrair Número do Processo
**Função:** `extract_process_number(task_name)`  
**Localização:** [dashboard.py](dashboard.py#L478-L490)

```python
# Regex para número de processo brasileiro
pattern = r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})'

# Exemplo:
extract_process_number("1234567-12.2024.1.23.4567 - JOÃO x EMPRESA")
# Retorna: "1234567-12.2024.1.23.4567"
```

---

## 🛡️ Tratamento de Erros e Segurança

### Validações implementadas:
1. **Credenciais OAuth2:**
   - Verifica existência de `credentials.json`
   - Atualiza token automaticamente se expirado
   - Salva token em `token.pickle`

2. **Configurações do MeisterTask:**
   - Valida `MEISTERTASK_API_TOKEN`
   - Valida `MEISTERTASK_SECTION_ID`
   - Exibe mensagem clara se não configurados

3. **Requisições HTTP:**
   - Timeout de 30 segundos
   - Try/catch em todas as operações
   - Mensagens de erro detalhadas

4. **Rate Limiting:**
   - Delay de 0.5 segundos entre criação de tarefas
   - Previne bloqueio pela API do MeisterTask

### Exemplos de tratamento:
```python
try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if response.status_code in [200, 201]:
        return True, response.json()
    else:
        error_detail = f"Status {response.status_code}: {response.text}"
        return False, error_detail
        
except requests.exceptions.RequestException as e:
    return False, f"Erro de conexão: {str(e)}"
```

---

## 🎯 Controle de Estado (Session State)

O sistema usa **Streamlit Session State** para manter dados entre interações:

### Estados principais:
```python
st.session_state = {
    'current_step': 1,                    # Etapa atual (1-4)
    'app_mode': 'criar_tarefas',         # Modo de operação
    'data_source': 'gmail',               # Fonte de dados
    'filtered_emails': [],                # Emails filtrados
    'selected_email_ids': [],             # IDs dos emails selecionados
    'extracted_publications': [],         # Publicações extraídas
    'selected_publication_ids': [],       # Publicações selecionadas
    'task_creation_results': None,        # Resultados da criação
    'tasks_to_delete': [],                # Tarefas para deletar
    'filters': {...}                      # Filtros aplicados
}
```

### Validação de consistência:
```python
# Não permite pular etapas
if st.session_state.current_step > 1 and not st.session_state.filtered_emails:
    st.session_state.current_step = 1

if st.session_state.current_step > 2 and not st.session_state.selected_email_ids:
    st.session_state.current_step = 1

if st.session_state.current_step > 3 and not st.session_state.extracted_publications:
    st.session_state.current_step = 1
```

---

## 📈 Estatísticas e Relatórios

### Após criação de tarefas:
```python
st.session_state.task_creation_results = {
    'success_count': 15,              # Tarefas criadas com sucesso
    'error_count': 2,                 # Erros encontrados
    'errors': [                       # Detalhes dos erros
        "1234567-12.2024.1.23.4567: Status 400: Invalid data",
        "7654321-98.2024.1.23.9876: Erro de conexão: Timeout"
    ],
    'success_tasks': [                # Processos criados
        "1234567-12.2024.1.23.4567",
        "2345678-23.2024.1.23.5678",
        ...
    ]
}
```

### Barra de progresso:
```python
for idx, pub in enumerate(selected_pubs):
    # Atualiza progresso visual
    progress = (idx + 1) / len(selected_pubs)
    progress_bar.progress(progress)
    status_text.text(f"Criando tarefa {idx + 1} de {len(selected_pubs)}")
    
    # Processa tarefa...
    time.sleep(0.5)  # Rate limiting
```

---

## 🔗 Dependências Necessárias

```python
# Interface
import streamlit as st

# Gmail API
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle

# Processamento de texto
import html2text
import base64
import re

# MeisterTask API
import requests

# Outros
import json, os, time, subprocess
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
```

---

## 📝 Configuração Necessária (.env)

```bash
# Gmail
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json

# MeisterTask
MEISTERTASK_API_TOKEN=seu_token_aqui
MEISTERTASK_PROJECT_ID=id_do_projeto
MEISTERTASK_SECTION_ID=id_da_secao

# Outros
PROCESSED_LABEL=Processado/MeisterTask
```

---

## 🚀 Otimizações Implementadas

1. **Cache de autenticação:** Token salvo em `token.pickle`
2. **Rate limiting:** Delay entre requisições
3. **Validação prévia:** Verifica configurações antes de executar
4. **Feedback visual:** Barra de progresso e contadores
5. **Persistência de resultados:** Session state mantém dados
6. **Múltiplos padrões regex:** Aumenta taxa de sucesso na extração
7. **Fallbacks:** Tratamento alternativo quando padrão principal falha

---

## 📌 Observações Importantes

1. **Um email pode gerar múltiplas tarefas** (se contiver várias publicações)
2. **Validação manual** em cada etapa garante qualidade
3. **Não há criação automática** - usuário sempre confirma
4. **Duplicatas podem ser gerenciadas** posteriormente
5. **Limitação do Gmail:** Máximo 50 emails por busca
6. **Limitação do MeisterTask:** Título com máximo 250 caracteres

---

## 🔍 Casos de Uso

### Caso 1: Email com múltiplas publicações
```
Input: 1 email com 5 publicações
Output: 5 tarefas no MeisterTask
```

### Caso 2: Busca por período
```
Filtro: Emails de 01/01/2026 a 15/01/2026
Resultado: Até 50 emails do período
```

### Caso 3: Gerenciamento de duplicatas
```
Identificação: 3 tarefas com mesmo processo
Ação: Usuário escolhe qual manter e deleta as outras
```

---

**Desenvolvido para:** Edson Pratti Advogados  
**Tecnologias:** Python, Streamlit, Gmail API, MeisterTask API  
**Versão:** 1.0  
**Última atualização:** 22/01/2026
