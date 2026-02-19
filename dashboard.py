#!/usr/bin/env python3
"""
Dashboard de Gerenciamento da Automação Gmail → MeisterTask
Sistema com validação manual em múltiplas etapas e gerenciamento de duplicatas
"""
import streamlit as st
import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import re
from openai import OpenAI
import html2text
import requests
from djne_scraper import buscar_publicacoes_djne

# Configuração da página
st.set_page_config(
    page_title="Automação Gmail → MeisterTask",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Tema visual ──────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    /* Fonte global */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

    /* Fundo principal — branco */
    .stApp { background-color: #ffffff; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f8f9fa !important;
        border-right: 1px solid #e5e7eb;
    }

    /* Botão primário */
    .stButton > button[kind="primary"] {
        background: #2563eb !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1d4ed8 !important;
        transform: translateY(-1px);
    }

    /* Botão secundário */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.15s ease;
    }

    /* Cards / expanders */
    .streamlit-expanderHeader {
        background: #f9fafb !important;
        border-radius: 10px !important;
        border: 1px solid #e5e7eb !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderContent {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stDateInput > div > div > input {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
    }

    /* Info / Warning / Success / Error boxes */
    .stAlert { border-radius: 8px !important; }

    /* Divisor */
    hr { border-color: #e5e7eb !important; }

    /* Métricas */
    [data-testid="metric-container"] {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 0.8rem 1rem;
    }

    /* Step badge */
    .step-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 6px;
        width: 100%;
    }
    .step-active  { background:#4f6ef722; color:#4f6ef7 !important; border:1px solid #4f6ef7; }
    .step-done    { background:#10b98122; color:#10b981 !important; border:1px solid #10b981; text-decoration: line-through; opacity: 0.7; }
    .step-pending { background:#f3f4f6; color:#9ca3af !important; border:1px solid #e5e7eb; }
</style>
""", unsafe_allow_html=True)

# Função para carregar variáveis do .env
def load_env_var(key, default=''):
    """Carrega variável do arquivo .env"""
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    k, v = line.strip().split('=', 1)
                    if k == key:
                        return v
    return default

# Inicializar session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1  # 1=Filtros, 2=Emails, 3=Publicações, 4=Tarefas

if 'app_mode' not in st.session_state:
    st.session_state.app_mode = 'criar_tarefas'  # 'criar_tarefas' ou 'gerenciar_duplicatas'

if 'data_source' not in st.session_state:
    st.session_state.data_source = 'gmail'  # 'gmail' ou 'djne'

if 'filtered_emails' not in st.session_state:
    st.session_state.filtered_emails = []

if 'selected_email_ids' not in st.session_state:
    st.session_state.selected_email_ids = []

if 'extracted_publications' not in st.session_state:
    st.session_state.extracted_publications = []

if 'selected_publication_ids' not in st.session_state:
    st.session_state.selected_publication_ids = []

if 'task_creation_results' not in st.session_state:
    st.session_state.task_creation_results = None

if 'tasks_to_delete' not in st.session_state:
    st.session_state.tasks_to_delete = []

if 'found_tasks' not in st.session_state:
    st.session_state.found_tasks = None

if 'found_duplicates' not in st.session_state:
    st.session_state.found_duplicates = None
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'text_search': '',
        'date_from': None,
        'date_to': None,
        'read_status': 'unread'  # unread, read, all
    }

if 'fonte_dados' not in st.session_state:
    st.session_state.fonte_dados = 'Gmail'  # Gmail ou DJNE

# Validação de consistência do estado
# Se está em etapas avançadas mas não tem dados, volta para o início
# EXCETO para DJNE que pula direto para etapa 3
if st.session_state.current_step > 1 and not st.session_state.filtered_emails and not st.session_state.extracted_publications:
    st.session_state.current_step = 1
if st.session_state.current_step > 2 and not st.session_state.selected_email_ids and not st.session_state.extracted_publications:
    st.session_state.current_step = 1
if st.session_state.current_step > 3 and not st.session_state.extracted_publications:
    st.session_state.current_step = 1
# Função para conectar ao Gmail
def get_gmail_service():
    """Conecta ao Gmail API"""
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

# Função para buscar emails com filtros
def search_emails(service, filters):
    """Busca emails baseado nos filtros"""
    if not service:
        return []
    
    query_parts = []
    
    # Filtro de texto (assunto ou corpo) - busca mais específica
    if filters.get('text_search'):
        # Busca no assunto OU no corpo do email
        query_parts.append(f'(subject:{filters["text_search"]} OR {filters["text_search"]})')
    
    # Filtro de data - ajusta para incluir as datas selecionadas
    # Gmail usa 'after' e 'before' de forma EXCLUSIVA, então ajustamos:
    if filters.get('date_from'):
        # Subtrai 1 dia para incluir a data selecionada
        date_obj = filters['date_from'] if hasattr(filters['date_from'], 'strftime') else datetime.strptime(filters['date_from'], '%Y/%m/%d').date()
        adjusted_date = date_obj - timedelta(days=1)
        query_parts.append(f'after:{adjusted_date.strftime("%Y/%m/%d")}')
    if filters.get('date_to'):
        # Adiciona 1 dia para incluir a data selecionada
        date_obj = filters['date_to'] if hasattr(filters['date_to'], 'strftime') else datetime.strptime(filters['date_to'], '%Y/%m/%d').date()
        adjusted_date = date_obj + timedelta(days=1)
        query_parts.append(f'before:{adjusted_date.strftime("%Y/%m/%d")}')
    
    # Filtro de lido/não lido
    if filters.get('read_status') == 'unread':
        query_parts.append('is:unread')
    elif filters.get('read_status') == 'read':
        query_parts.append('is:read')
    
    query = ' '.join(query_parts) if query_parts else 'in:inbox'
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()
        
        messages = results.get('messages', [])
        
        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Sem assunto')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Desconhecido')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Sem data')
            
            # Extrair corpo do email
            body = extract_email_body(msg_data)
            
            # Verificar se está lido
            is_read = 'UNREAD' not in msg_data.get('labelIds', [])
            
            email_list.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'is_read': is_read,
                'raw_data': msg_data
            })
        
        return email_list
    
    except Exception as e:
        st.error(f"Erro ao buscar emails: {str(e)}")
        return []

# Função para extrair corpo do email
def extract_email_body(message):
    """Extrai o corpo do email e converte HTML para texto plano"""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_emphasis = False
    h.body_width = 0  # Sem quebra de linha automática
    
    try:
        if 'parts' in message['payload']:
            parts = message['payload']['parts']
            body = ''
            html_body = ''
            
            # Prioriza text/plain, mas guarda HTML como fallback
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        html_body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            
            # Se não tem text/plain, converte HTML para texto
            if not body and html_body:
                body = h.handle(html_body)
            
            return body
        else:
            if 'data' in message['payload']['body']:
                raw_data = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
                # Se parece com HTML, converte para texto
                if raw_data.strip().startswith('<'):
                    return h.handle(raw_data)
                return raw_data
    except:
        return "Não foi possível extrair o corpo do email"
    
    return ""

# Função para extrair publicações de um email
def extract_publications_from_email(email_body, email_subject):
    """
    Extrai múltiplas publicações de processos judiciais de um email
    Usa APENAS números como separadores (Publicação: 1, 2, 3...)
    Ignora "Publicação: Intimacao" e similares
    """
    publications = []
    
    # Padrão SIMPLES e DIRETO: Publicação seguido de número
    pattern = r'Publicação:\s*(\d+)\s+'
    pub_matches = list(re.finditer(pattern, email_body, re.IGNORECASE))
    
    if pub_matches:
        for i, match in enumerate(pub_matches):
            start_pos = match.start()
            end_pos = pub_matches[i + 1].start() if i + 1 < len(pub_matches) else len(email_body)
            pub_content = email_body[start_pos:end_pos].strip()
            
            process_pattern_marked = r'PROCESSO:\s*(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
            process_match_marked = re.search(process_pattern_marked, pub_content, re.IGNORECASE)
            if process_match_marked:
                process_number = process_match_marked.group(1)
            else:
                process_pattern = r'(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
                process_match = re.search(process_pattern, pub_content)
                process_number = process_match.group(0) if process_match else f'Publicação {match.group(1)}'
            
            publications.append({
                'process_number': process_number,
                'content': pub_content,
                'source_subject': email_subject
            })
        return publications
    
    # Tenta 'PROCESSO:' como separador
    process_pattern = r'PROCESSO:\s*(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
    process_matches = list(re.finditer(process_pattern, email_body, re.IGNORECASE))
    if process_matches:
        for i, match in enumerate(process_matches):
            process_number = match.group(1)
            start = max(0, match.start() - 200)
            end = process_matches[i + 1].start() if i + 1 < len(process_matches) else len(email_body)
            pub_content = email_body[start:end].strip()
            publications.append({
                'process_number': process_number,
                'content': pub_content,
                'source_subject': email_subject
            })
        return publications
    
    # Fallback: padrão direto de processo
    process_pattern_simple = r'\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4}'
    process_matches_simple = list(re.finditer(process_pattern_simple, email_body))
    if process_matches_simple:
        for match in process_matches_simple:
            process_number = match.group(0)
            start = max(0, match.start() - 200)
            end = min(len(email_body), match.end() + 1500)
            pub_content = email_body[start:end].strip()
            publications.append({
                'process_number': process_number,
                'content': pub_content,
                'source_subject': email_subject
            })
        return publications
    
    # Nenhum padrão encontrado — trata como publicação única
    publications.append({
        'process_number': 'Sem número identificado',
        'content': email_body[:5000],
        'source_subject': email_subject
    })
    return publications

# Função para extrair nomes das partes de uma publicação
def extract_parties_from_publication(pub_content):
    """
    Extrai nomes das partes (autor/requerente vs réu/requerido) de uma publicação
    """
    parties = ""
    
    # Padrões comuns para identificar partes
    patterns = [
        # REQUERENTE: NOME vs REQUERIDO: NOME
        r'REQUERENTE:\s*([^\n]+).*?REQUERIDO:\s*([^\n]+)',
        # EXEQUENTE: NOME vs EXECUTADO: NOME
        r'EXEQUENTE:\s*([^\n]+).*?EXECUTADO:\s*([^\n]+)',
        # AUTOR: NOME vs RÉU: NOME
        r'AUTOR:\s*([^\n]+).*?R[ÉE]U:\s*([^\n]+)',
        # APELANTE: NOME vs APELADO: NOME
        r'APELANTE:\s*([^\n]+).*?APELADO:\s*([^\n]+)',
        # RECORRENTE: NOME vs RECORRIDO: NOME
        r'RECORRENTE:\s*([^\n]+).*?RECORRIDO:\s*([^\n]+)',
        # EMBARGANTE: NOME vs EMBARGADO: NOME
        r'EMBARGANTE:\s*([^\n]+).*?EMBARGADO:\s*([^\n]+)',
        # AGRAVANTE: NOME vs AGRAVADO: NOME
        r'AGRAVANTE:\s*([^\n]+).*?AGRAVADO:\s*([^\n]+)',
        # INTERESSADO: NOME vs INTERESSADO: NOME (segunda parte)
        r'INTERESSADO:\s*([^\n]+).*?INTERESSADO:\s*([^\n]+)',
        # IMPETRADO vs IMPETRANTE
        r'IMPETRANTE:\s*([^\n]+).*?IMPETRADO:\s*([^\n]+)',
        # CONSULENTE: NOME vs CONSULADO: NOME
        r'CONSULENTE:\s*([^\n]+).*?CONSULADO:\s*([^\n]+)',
        # Partes: NOME vs NOME
        r'Partes:\s*([^\n]+?)\s+vs\s+([^\n]+)',
        # Parte Autora vs Parte Ré (genérico)
        r'Parte\s+(?:Autora|Ativa):\s*([^\n]+).*?Parte\s+(?:R[ée]|Passiva):\s*([^\n]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, pub_content, re.IGNORECASE | re.DOTALL)
        if match:
            party1 = match.group(1).strip()
            party2 = match.group(2).strip()
            
            # Remove CPF/CNPJ e números
            party1 = re.sub(r'\d{11,}', '', party1).strip()
            party2 = re.sub(r'\d{11,}', '', party2).strip()
            
            # Limita tamanho
            if len(party1) > 50:
                party1 = party1[:50].strip()
            if len(party2) > 50:
                party2 = party2[:50].strip()
            
            parties = f"{party1} x {party2}"
            break
    
    # Se não encontrou padrão, tenta pegar primeiros nomes encontrados
    if not parties:
        # Procura por linhas que começam com POLO ATIVO/PASSIVO
        polo_ativo = re.search(r'POLO ATIVO:\s*([^\n]+)', pub_content, re.IGNORECASE)
        polo_passivo = re.search(r'POLO PASSIVO:\s*([^\n]+)', pub_content, re.IGNORECASE)
        
        if polo_ativo and polo_passivo:
            party1 = polo_ativo.group(1).strip()[:50]
            party2 = polo_passivo.group(1).strip()[:50]
            parties = f"{party1} x {party2}"
    
    # Se ainda não encontrou, tenta buscar padrão genérico de qualquer parte
    if not parties:
        # Busca por palavras-chave de tipos de partes (captura múltiplas ocorrências)
        parte_keywords = r'(?:INTERESSADO|APELANTE|APELADO|RECORRENTE|RECORRIDO|REQUERENTE|REQUERIDO|EXEQUENTE|EXECUTADO|AUTOR|R[ÉE]U|EMBARGANTE|EMBARGADO|AGRAVANTE|AGRAVADO|IMPETRANTE|IMPETRADO)'
        matches = re.findall(rf'{parte_keywords}[:\s]+([^\n]+)', pub_content, re.IGNORECASE)
        
        if len(matches) >= 2:
            # Pega as duas primeiras partes encontradas
            party1 = matches[0].strip()
            party2 = matches[1].strip()
            
            # Remove CPF/CNPJ e números
            party1 = re.sub(r'\d{11,}', '', party1).strip()
            party2 = re.sub(r'\d{11,}', '', party2).strip()
            
            # Limita tamanho
            if len(party1) > 50:
                party1 = party1[:50].strip()
            if len(party2) > 50:
                party2 = party2[:50].strip()
            
            parties = f"{party1} x {party2}"
    
    return parties if parties else "Partes não identificadas"

# Função para criar tarefa no MeisterTask
def create_meistertask_task(process_number, parties, description, section_id, api_token):
    """
    Cria uma tarefa no MeisterTask via API
    """
    url = f"https://www.meistertask.com/api/sections/{section_id}/tasks"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # Título: [numero do processo] - [nome das partes]
    title = f"{process_number} - {parties}"
    
    # Limita tamanho do título (MeisterTask tem limite)
    if len(title) > 250:
        title = title[:247] + "..."
    
    payload = {
        "name": title,
        "notes": description
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # MeisterTask retorna 200 ou 201 para sucesso
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            error_detail = f"Status {response.status_code}: {response.text}"
            return False, error_detail
            
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"


def list_meistertask_tasks(section_id, api_token):
    """
    Lista TODAS as tarefas de uma seção do MeisterTask (com paginação)
    A API retorna no máximo 50 tarefas por página, então precisamos fazer múltiplas requisições
    """
    # Validação básica dos parâmetros
    if not section_id or not api_token:
        return False, "❌ Section ID ou API Token não configurados"
    
    all_tasks = []
    page = 1
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        while True:
            # MeisterTask usa offset/limit ao invés de page/per_page
            offset = (page - 1) * 50
            url = f"https://www.meistertask.com/api/sections/{section_id}/tasks"
            
            # Tenta com parâmetros de paginação
            params = {"limit": 100, "offset": offset}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                tasks = response.json()
                
                # Se não retornou tarefas, chegamos ao fim
                if not tasks or len(tasks) == 0:
                    break
                
                all_tasks.extend(tasks)
                
                # Se retornou menos que 50, é a última página
                if len(tasks) < 50:
                    break
                
                # Vai para próxima página
                page += 1
                
                # Proteção contra loop infinito
                if page > 20:  # Máximo 1000 tarefas (20 páginas x 50)
                    break
            
            elif response.status_code == 404:
                # Section ID inválido ou não existe
                error_msg = f"""
❌ **Erro 404: Seção não encontrada**

A seção com ID `{section_id}` não existe ou você não tem acesso a ela.

**Possíveis causas:**
1. O `MEISTERTASK_SECTION_ID` no arquivo `.env` está incorreto
2. A seção foi deletada do MeisterTask
3. Você não tem permissão para acessar esta seção

**Como corrigir:**
1. Acesse o MeisterTask no navegador
2. Vá até o quadro/projeto desejado
3. Abra a seção "Publicações" (ou outra que deseja usar)
4. Copie o ID da seção da URL (número após `/sections/`)
5. Atualize o valor de `MEISTERTASK_SECTION_ID` no arquivo `.env`

**ID atual configurado:** `{section_id}`
"""
                return False, error_msg
            
            elif response.status_code == 401:
                # Token inválido ou expirado
                error_msg = """
❌ **Erro 401: Não autorizado**

O token de API está inválido ou expirado.

**Como corrigir:**
1. Acesse o MeisterTask: Account Settings → Developer
2. Gere um novo token de API
3. Atualize `MEISTERTASK_API_TOKEN` no arquivo `.env`
"""
                return False, error_msg
            
            elif response.status_code == 403:
                # Sem permissão
                return False, f"❌ Erro 403: Sem permissão para acessar a seção {section_id}"
            
            else:
                # Outros erros
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get('message', response.text[:200])
                except:
                    error_msg = response.text[:200]
                return False, f"❌ Erro HTTP {response.status_code}: {error_msg}"
        
        return True, all_tasks
            
    except requests.exceptions.Timeout:
        return False, "❌ Timeout: A requisição demorou mais de 30 segundos"
    except requests.exceptions.ConnectionError:
        return False, "❌ Erro de conexão: Verifique sua internet"
    except requests.exceptions.RequestException as e:
        return False, f"❌ Erro de conexão: {str(e)}"


def get_meistertask_task(task_id, api_token):
    """
    Busca informações de uma tarefa específica do MeisterTask
    """
    url = f"https://www.meistertask.com/api/tasks/{task_id}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            return False, "404_NOT_FOUND"
        else:
            return False, f"HTTP_{response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return False, f"CONNECTION_ERROR: {str(e)}"


def delete_meistertask_task(task_id, api_token):
    """
    Move uma tarefa do MeisterTask para a lixeira (trash)
    A API do MeisterTask usa PUT com status=18 para enviar tarefas para a lixeira
    
    Retorna:
        (bool, str): (sucesso, mensagem)
        - True se a tarefa foi deletada ou já estava deletada (404)
        - False apenas se houver um erro real que impeça a operação
    """
    url = f"https://www.meistertask.com/api/tasks/{task_id}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Tenta mover para lixeira (trash) usando status=18
        trash_data = {"status": 18}
        response = requests.put(url, headers=headers, json=trash_data, timeout=30)
        
        if response.status_code in [200, 204]:
            # Sucesso: tarefa movida para lixeira
            if response.status_code == 200:
                try:
                    result = response.json()
                    new_status = result.get('status', 'unknown')
                    return True, f"✓ Tarefa ID {task_id[:8]}... movida para lixeira (status: {new_status})"
                except:
                    return True, f"✓ Tarefa ID {task_id[:8]}... movida para lixeira"
            return True, f"✓ Tarefa ID {task_id[:8]}... deletada com sucesso"
        
        elif response.status_code == 404:
            # 404 NOT_FOUND: tarefa já foi deletada anteriormente ou nunca existiu
            # Consideramos como SUCESSO pois o objetivo (tarefa não existir) foi alcançado
            return True, f"⚠ Tarefa ID {task_id[:8]}... já estava deletada (404: NOT_FOUND)"
        
        elif response.status_code == 403:
            # 403 FORBIDDEN: sem permissão
            return False, f"✗ Sem permissão para deletar tarefa ID {task_id[:8]}... (403: FORBIDDEN)"
        
        elif response.status_code == 400:
            # 400 BAD_REQUEST: parâmetros inválidos
            try:
                error_detail = response.json()
                error_msg = error_detail.get('message', response.text[:200])
            except:
                error_msg = response.text[:200]
            return False, f"✗ Requisição inválida para tarefa ID {task_id[:8]}... (400): {error_msg}"
        
        else:
            # Outros erros HTTP
            try:
                error_msg = response.text[:200]
            except:
                error_msg = "Resposta não disponível"
            return False, f"✗ Erro HTTP {response.status_code} ao deletar tarefa ID {task_id[:8]}...: {error_msg}"
            
    except requests.exceptions.Timeout:
        return False, f"✗ Timeout ao deletar tarefa ID {task_id[:8]}... (>30s)"
    except requests.exceptions.ConnectionError:
        return False, f"✗ Erro de conexão ao deletar tarefa ID {task_id[:8]}..."
    except requests.exceptions.RequestException as e:
        return False, f"✗ Erro de rede ao deletar tarefa ID {task_id[:8]}...: {str(e)[:100]}"


def extract_process_number(task_name):
    """
    Extrai o número do processo do nome da tarefa.
    Formato esperado: "XXXXXXX-XX.XXXX.X.XX.XXXX - Nome das Partes"
    Aceita variações com 1 ou 2 dígitos no segmento do meio
    """
    import re
    # Padrão mais flexível para número de processo brasileiro
    # Aceita: NNNNNNN-DD.AAAA.J.TT.OOOO onde J pode ser 1 ou 2 dígitos
    pattern = r'(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})'
    match = re.search(pattern, task_name)
    if match:
        return match.group(1)
    return None


def find_duplicate_tasks(tasks, only_unassigned=True):
    """
    Identifica tarefas duplicadas baseadas no número do processo
    Retorna um dicionário: {numero_processo: [lista de tarefas]}
    
    Args:
        tasks: Lista de tarefas do MeisterTask
        only_unassigned: Se True, considera apenas tarefas sem responsável designado
    """
    # Primeiro, filtra tarefas sem responsável se solicitado
    if only_unassigned:
        filtered_tasks = [task for task in tasks if not task.get('assigned_to_id')]
    else:
        filtered_tasks = tasks
    
    process_dict = {}
    seen_task_ids = set()
    tasks_without_process = []  # Tarefas sem número de processo válido
    
    for task in filtered_tasks:
        task_id = task.get('id')
        task_name = task.get('name', '')
        
        # Pula se já vimos esta tarefa
        if task_id in seen_task_ids:
            continue
        
        process_number = extract_process_number(task_name)
        
        # Só agrupa tarefas que TÊM número de processo válido
        if process_number:
            if process_number not in process_dict:
                process_dict[process_number] = []
            
            process_dict[process_number].append(task)
            seen_task_ids.add(task_id)
        else:
            # Tarefa sem número de processo - não agrupa
            tasks_without_process.append(task_name[:80])
    
    # Filtra APENAS processos que têm MAIS DE UMA tarefa
    duplicates = {k: v for k, v in process_dict.items() if len(v) > 1}
    
    return duplicates
# =============================================================================
# SESSION STATE — navegação por páginas
# =============================================================================
if 'page' not in st.session_state:
    st.session_state.page = 'home'  # home | source_select | flow | duplicatas
if 'fonte_dados' not in st.session_state:
    st.session_state.fonte_dados = None  # 'Gmail' | 'DJNE'
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'filtered_emails' not in st.session_state:
    st.session_state.filtered_emails = []
if 'selected_email_ids' not in st.session_state:
    st.session_state.selected_email_ids = []
if 'extracted_publications' not in st.session_state:
    st.session_state.extracted_publications = []
if 'selected_publication_ids' not in st.session_state:
    st.session_state.selected_publication_ids = []
if 'task_creation_results' not in st.session_state:
    st.session_state.task_creation_results = None
if 'found_tasks' not in st.session_state:
    st.session_state.found_tasks = None
if 'found_duplicates' not in st.session_state:
    st.session_state.found_duplicates = None
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'text_search': '',
        'date_from': None,
        'date_to': None,
        'read_status': 'unread'
    }

def go(page, reset_flow=False):
    st.session_state.page = page
    if reset_flow:
        st.session_state.current_step = 1
        st.session_state.filtered_emails = []
        st.session_state.selected_email_ids = []
        st.session_state.extracted_publications = []
        st.session_state.selected_publication_ids = []
        st.session_state.task_creation_results = None
        st.session_state.fonte_dados = None
    st.rerun()

# Helper: botão de voltar ao início (sidebar minimalista)
def render_sidebar_back():
    with st.sidebar:
        if st.button('← Início', use_container_width=True):
            go('home', reset_flow=True)

# =============================================================================
# PÁGINA: HOME
# =============================================================================
if st.session_state.page == 'home':
    # Centraliza o conteúdo
    st.markdown('<div style="height:3rem"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center; margin-bottom:2.5rem;">
        <h1 style="font-size:2rem; font-weight:700; color:#111827; margin:0;">📧 Gmail → MeisterTask</h1>
        <p style="color:#6b7280; margin-top:6px;">O que você quer fazer hoje?</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col1, col2, col_r = st.columns([1, 2, 2, 1])

    with col1:
        st.markdown("""
        <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:16px;
                    padding:2rem; text-align:center; height:180px;
                    display:flex; flex-direction:column; justify-content:center; gap:12px;">
            <div style="font-size:2.5rem;">➕</div>
            <div style="font-size:1.1rem; font-weight:700; color:#111827;">Criar Tarefas</div>
            <div style="font-size:0.82rem; color:#6b7280;">Importar publicações e gerar tarefas no MeisterTask</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        if st.button('Criar Tarefas', use_container_width=True, type='primary', key='btn_criar'):
            go('source_select', reset_flow=True)

    with col2:
        st.markdown("""
        <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:16px;
                    padding:2rem; text-align:center; height:180px;
                    display:flex; flex-direction:column; justify-content:center; gap:12px;">
            <div style="font-size:2.5rem;">🔍</div>
            <div style="font-size:1.1rem; font-weight:700; color:#111827;">Gerenciar Duplicatas</div>
            <div style="font-size:0.82rem; color:#6b7280;">Identificar e remover tarefas duplicadas</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        if st.button('Gerenciar Duplicatas', use_container_width=True, key='btn_dup'):
            go('duplicatas')

# =============================================================================
# PÁGINA: ESCOLHA DA FONTE DE DADOS
# =============================================================================
elif st.session_state.page == 'source_select':
    render_sidebar_back()

    st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center; margin-bottom:2.5rem;">
        <h1 style="font-size:1.6rem; font-weight:700; color:#111827; margin:0;">De onde vêm as publicações?</h1>
        <p style="color:#6b7280; margin-top:6px;">Escolha a fonte de dados</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col1, col2, col_r = st.columns([1, 2, 2, 1])

    with col1:
        st.markdown("""
        <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:16px;
                    padding:2rem; text-align:center; height:160px;
                    display:flex; flex-direction:column; justify-content:center; gap:10px;">
            <div style="font-size:2.2rem;">📧</div>
            <div style="font-size:1.05rem; font-weight:700; color:#111827;">Gmail</div>
            <div style="font-size:0.80rem; color:#6b7280;">Buscar publicações nos e-mails recebidos</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        if st.button('Usar Gmail', use_container_width=True, type='primary', key='btn_gmail'):
            st.session_state.fonte_dados = 'Gmail'
            st.session_state.current_step = 1
            go('flow')

    with col2:
        st.markdown("""
        <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:16px;
                    padding:2rem; text-align:center; height:160px;
                    display:flex; flex-direction:column; justify-content:center; gap:10px;">
            <div style="font-size:2.2rem;">⚖️</div>
            <div style="font-size:1.05rem; font-weight:700; color:#111827;">DJNE</div>
            <div style="font-size:0.80rem; color:#6b7280;">Buscar diretamente no Diário de Justiça Eletrônico</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        if st.button('Usar DJNE', use_container_width=True, type='primary', key='btn_djne'):
            st.session_state.fonte_dados = 'DJNE'
            st.session_state.current_step = 1
            go('flow')

# =============================================================================
# PÁGINA: FLUXO DE CRIAÇÃO DE TAREFAS
# =============================================================================
elif st.session_state.page == 'flow':
    render_sidebar_back()
    fonte = st.session_state.fonte_dados

    # ── Cabeçalho com progresso ──────────────────────────────────────────────
    steps_labels = ['Filtrar', 'Selecionar', 'Validar', 'Gerar']
    current = st.session_state.current_step
    fonte_icon = '📧' if fonte == 'Gmail' else '⚖️'

    cols_prog = st.columns(4)
    for i, label in enumerate(steps_labels):
        step_num = i + 1
        with cols_prog[i]:
            if step_num == current:
                st.markdown(f'<div style="text-align:center; color:#4f6ef7; font-weight:700; font-size:0.85rem; border-bottom:2px solid #4f6ef7; padding-bottom:6px;">▶ {label}</div>', unsafe_allow_html=True)
            elif step_num < current:
                st.markdown(f'<div style="text-align:center; color:#10b981; font-size:0.85rem; padding-bottom:6px;">✓ {label}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="text-align:center; color:#9ca3af; font-size:0.85rem; padding-bottom:6px;">{label}</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)

    # ── ETAPA 1: Filtros ─────────────────────────────────────────────────────
    if current == 1:
        st.subheader(f"{fonte_icon} Filtros de Busca — {fonte}")
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

        if fonte == 'Gmail':
            col1, col2, col3 = st.columns(3)
            with col1:
                text_search = st.text_input('Buscar no assunto / corpo',
                    value=st.session_state.filters.get('text_search', ''),
                    placeholder='Ex: intimação, publicação...')
            with col2:
                date_from = st.date_input('De:', value=st.session_state.filters.get('date_from') or (datetime.now() - timedelta(days=7)).date())
                date_to   = st.date_input('Até:', value=st.session_state.filters.get('date_to') or datetime.now().date())
            with col3:
                read_status = st.radio('Status dos e-mails:', ['unread', 'read', 'all'],
                    format_func=lambda x: {'unread':'📭 Não lidos','read':'📬 Lidos','all':'📧 Todos'}[x],
                    index=['unread','read','all'].index(st.session_state.filters.get('read_status','unread')))
        else:  # DJNE
            text_search = ''
            read_status = 'all'
            nome_adv = load_env_var('DJNE_NOME_ADVOGADO', 'EDSON MARCOS FERREIRA PRATTI JUNIOR')
            col1, col2 = st.columns(2)
            with col1:
                st.info(f'👤 **Advogado:** {nome_adv}')
            with col2:
                date_from = st.date_input('De:', value=st.session_state.filters.get('date_from') or datetime.now().date())
                date_to   = st.date_input('Até:', value=st.session_state.filters.get('date_to') or datetime.now().date())

        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
        _, col_btn, _ = st.columns([2,1,2])
        with col_btn:
            btn_label = '🔍 Buscar no Gmail' if fonte == 'Gmail' else '🔍 Buscar no DJNE'
            if st.button(btn_label, use_container_width=True, type='primary'):
                st.session_state.filters = {
                    'text_search': text_search if fonte == 'Gmail' else '',
                    'date_from': date_from,
                    'date_to': date_to,
                    'read_status': read_status if fonte == 'Gmail' else 'all'
                }

                if fonte == 'Gmail':
                    with st.spinner('Buscando e-mails...'):
                        gmail_service = get_gmail_service()
                        if gmail_service:
                            emails = search_emails(gmail_service, st.session_state.filters)
                            st.session_state.filtered_emails = emails
                            if emails:
                                st.session_state.current_step = 2
                                st.rerun()
                            else:
                                st.warning('Nenhum e-mail encontrado com esses filtros.')
                        else:
                            st.error('❌ Não foi possível conectar ao Gmail. Verifique a autenticação.')
                else:  # DJNE
                    with st.spinner('Buscando no DJNE...'):
                        try:
                            nome_adv = load_env_var('DJNE_NOME_ADVOGADO', 'EDSON MARCOS FERREIRA PRATTI JUNIOR')
                            publicacoes = buscar_publicacoes_djne(nome_adv, date_from, date_to)
                            for idx, pub in enumerate(publicacoes):
                                pub.update({
                                    'email_id': f'djne_{idx}',
                                    'email_subject': pub.get('source_subject', f"DJNE - {pub.get('process_number','')}"),
                                    'email_sender': 'DJNE',
                                    'email_date': pub.get('data_disponibilizacao', ''),
                                    'pub_id': f'djne_{idx}',
                                    'origem': 'DJNE'
                                })
                            st.session_state.extracted_publications = publicacoes
                            if publicacoes:
                                st.success(f'✅ {len(publicacoes)} publicações encontradas!')
                                st.session_state.current_step = 3
                                time.sleep(0.8)
                                st.rerun()
                            else:
                                st.warning('Nenhuma publicação encontrada para este período.')
                        except Exception as e:
                            st.error(f'❌ Erro ao buscar no DJNE: {str(e)}')

    # ── ETAPA 2: Selecionar e-mails ──────────────────────────────────────────
    elif current == 2:
        st.subheader(f'📬 Selecione os e-mails ({len(st.session_state.filtered_emails)} encontrados)')

        for email in st.session_state.filtered_emails:
            icon = '✉️' if not email['is_read'] else '📬'
            with st.expander(f"{icon} {email['subject'][:90]}  —  {email['sender'][:50]}", expanded=False):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"**De:** {email['sender']}   |   **Data:** {email['date']}")
                    body_preview = email['body'][:500] + '...' if len(email['body']) > 500 else email['body']
                    st.text_area('Conteúdo', value=body_preview, height=180, key=f"body_{email['id']}", disabled=True)
                with col2:
                    selected = st.checkbox('Selecionar', value=email['id'] in st.session_state.selected_email_ids, key=f"sel_{email['id']}")
                    if selected and email['id'] not in st.session_state.selected_email_ids:
                        st.session_state.selected_email_ids.append(email['id'])
                    elif not selected and email['id'] in st.session_state.selected_email_ids:
                        st.session_state.selected_email_ids.remove(email['id'])

        st.markdown('---')
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button('← Voltar', use_container_width=True):
                st.session_state.current_step = 1
                st.rerun()
        with col3:
            n = len(st.session_state.selected_email_ids)
            if st.button(f'📤 Extrair publicações ({n} selecionados)', use_container_width=True, type='primary', disabled=n == 0):
                with st.spinner('Extraindo publicações...'):
                    publications = []
                    for email in st.session_state.filtered_emails:
                        if email['id'] in st.session_state.selected_email_ids:
                            email_pubs = extract_publications_from_email(email['body'], email['subject'])
                            for pub in email_pubs:
                                pub.update({
                                    'email_id': email['id'],
                                    'email_subject': email['subject'],
                                    'email_sender': email['sender'],
                                    'email_date': email['date'],
                                    'pub_id': f"{email['id']}_{len(publications)}",
                                    'origem': 'Gmail'
                                })
                                publications.append(pub)
                    st.session_state.extracted_publications = publications
                    if publications:
                        st.session_state.current_step = 3
                        st.rerun()
                    else:
                        st.warning('Nenhuma publicação encontrada nos e-mails selecionados.')

    # ── ETAPA 3: Validar publicações ─────────────────────────────────────────
    elif current == 3:
        pubs = st.session_state.extracted_publications
        st.subheader(f'📋 Validar publicações ({len(pubs)} encontradas)')

        for pub in pubs:
            is_sel = pub['pub_id'] in st.session_state.selected_publication_ids
            icon = '✅' if is_sel else '📄'
            with st.expander(f"{icon} {pub['process_number']}  —  {pub.get('email_subject','')[:60]}", expanded=False):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"**Data:** {pub.get('email_date','')}  |  **Origem:** {pub.get('origem','')}")
                    if pub.get('origem') == 'DJNE':
                        if pub.get('tribunal'): st.caption(f"**Tribunal:** {pub['tribunal']}")
                        if pub.get('orgao'):    st.caption(f"**Órgão:** {pub['orgao']}")
                    st.text_area('Conteúdo', value=pub['content'], height=250,
                                 key=f"pc_{pub['pub_id']}", disabled=True)
                with col2:
                    sel = st.checkbox('Incluir', value=is_sel, key=f"sp_{pub['pub_id']}")
                    if sel and pub['pub_id'] not in st.session_state.selected_publication_ids:
                        st.session_state.selected_publication_ids.append(pub['pub_id'])
                    elif not sel and pub['pub_id'] in st.session_state.selected_publication_ids:
                        st.session_state.selected_publication_ids.remove(pub['pub_id'])

        st.markdown('---')
        volta_passo = 1 if st.session_state.fonte_dados == 'DJNE' else 2
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button('← Voltar', use_container_width=True):
                st.session_state.current_step = volta_passo
                st.rerun()
        with col3:
            n = len(st.session_state.selected_publication_ids)
            if st.button(f'✅ Gerar tarefas ({n} selecionadas)', use_container_width=True, type='primary', disabled=n == 0):
                st.session_state.current_step = 4
                st.rerun()

    # ── ETAPA 4: Gerar tarefas ───────────────────────────────────────────────
    elif current == 4:
        selected_pubs = [
            p for p in st.session_state.extracted_publications
            if p['pub_id'] in st.session_state.selected_publication_ids
        ]

        if not selected_pubs:
            st.warning('Nenhuma publicação selecionada.')
            if st.button('← Voltar'):
                st.session_state.current_step = 3
                st.rerun()
        else:
            st.subheader(f'🚀 Gerar {len(selected_pubs)} tarefa(s) no MeisterTask')

            with st.expander('Preview das tarefas', expanded=False):
                for i, pub in enumerate(selected_pubs, 1):
                    parties = extract_parties_from_publication(pub['content'])
                    st.code(f"{i}. {pub['process_number']} — {parties}")

            col1, col2 = st.columns(2)
            with col1:
                st.info('📁 **Projeto:** Edson Pratti Advogados')
            with col2:
                st.info('📌 **Seção:** Publicações')

            st.markdown('---')
            col_back, col_act = st.columns([1, 2])
            with col_back:
                if st.button('← Voltar', use_container_width=True):
                    st.session_state.current_step = 3
                    st.rerun()
            with col_act:
                if st.button(f'🚀 Criar {len(selected_pubs)} tarefa(s)', use_container_width=True, type='primary'):
                    api_token  = load_env_var('MEISTERTASK_API_TOKEN')
                    section_id = load_env_var('MEISTERTASK_SECTION_ID')

                    if not api_token or not section_id:
                        st.error('❌ Configure MEISTERTASK_API_TOKEN e MEISTERTASK_SECTION_ID no arquivo .env')
                    else:
                        progress_bar = st.progress(0)
                        status_text  = st.empty()
                        success_count, error_count = 0, 0
                        errors, success_tasks = [], []

                        for idx, pub in enumerate(selected_pubs):
                            progress_bar.progress((idx + 1) / len(selected_pubs))
                            status_text.text(f'Criando {idx+1}/{len(selected_pubs)}: {pub["process_number"]}')
                            parties = extract_parties_from_publication(pub['content'])
                            ok, result = create_meistertask_task(
                                pub['process_number'], parties, pub['content'], section_id, api_token
                            )
                            if ok:
                                success_count += 1
                                success_tasks.append(pub['process_number'])
                            else:
                                error_count += 1
                                errors.append(f"{pub['process_number']}: {result}")
                            time.sleep(0.5)

                        progress_bar.empty()
                        status_text.empty()
                        st.session_state.task_creation_results = {
                            'success_count': success_count,
                            'error_count': error_count,
                            'errors': errors,
                            'success_tasks': success_tasks
                        }

            # Resultados
            if st.session_state.task_creation_results:
                r = st.session_state.task_creation_results
                st.markdown('---')
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"✅ {r['success_count']} tarefa(s) criada(s)")
                    if r['success_tasks']:
                        with st.expander('Ver tarefas criadas'):
                            for t in r['success_tasks']: st.text(f'✓ {t}')
                with col2:
                    if r['error_count'] > 0:
                        st.error(f"❌ {r['error_count']} erro(s)")
                        with st.expander('Ver erros', expanded=True):
                            for e in r['errors']: st.code(e, language=None)

                st.markdown('---')
                if st.button('🏠 Voltar ao início', use_container_width=True, type='primary'):
                    go('home', reset_flow=True)

# =============================================================================
# PÁGINA: GERENCIAR DUPLICATAS
# =============================================================================
elif st.session_state.page == 'duplicatas':
    render_sidebar_back()

    st.subheader('🔍 Gerenciar Duplicatas')
    st.caption('Identifica e remove tarefas com o mesmo número de processo na seção **Publicações**.')
    st.markdown('---')

    api_token  = load_env_var('MEISTERTASK_API_TOKEN')
    section_id = load_env_var('MEISTERTASK_SECTION_ID')

    col1, col2 = st.columns(2)
    with col1:
        if api_token: st.success(f'🔑 API Token configurado (`...{api_token[-8:]}`)')
        else:         st.error('🔑 API Token não configurado')
    with col2:
        if section_id: st.success(f'📌 Section ID: `{section_id}`')
        else:          st.error('📌 Section ID não configurado')

    if not api_token or not section_id:
        st.error('Configure as variáveis no arquivo `.env` para continuar.')
    else:
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            if st.button('🔄 Buscar tarefas', use_container_width=True, type='primary'):
                with st.spinner('Buscando tarefas...'):
                    ok, result = list_meistertask_tasks(section_id, api_token)
                    if ok:
                        st.session_state.found_tasks = result
                        st.session_state.found_duplicates = find_duplicate_tasks(result)
                        st.success(f'{len(result)} tarefas carregadas.')
                    else:
                        st.error(f'Erro: {result}')

        if st.session_state.found_duplicates:
            duplicates = st.session_state.found_duplicates
            st.warning(f'⚠️ {len(duplicates)} processo(s) com duplicatas encontrados.')
            st.markdown('---')
            st.info('Marque as tarefas que deseja **MANTER**. As desmarcadas serão excluídas.')

            tasks_to_keep = []
            for p_idx, (proc_num, task_list) in enumerate(duplicates.items()):
                with st.expander(f'📂 {proc_num}  ({len(task_list)} duplicatas)', expanded=True):
                    for idx, task in enumerate(task_list, 1):
                        task_id = task.get('id')
                        col_ck, col_info = st.columns([1, 9])
                        with col_ck:
                            if st.checkbox('Manter', value=(idx == 1),
                                           key=f'keep_{p_idx}_{idx}_{task_id}',
                                           label_visibility='collapsed'):
                                tasks_to_keep.append(task_id)
                        with col_info:
                            created = task.get('created_at', '')[:10]
                            st.markdown(f'**{idx}.** `{task.get("name","")}` — criada em {created}')

            all_ids    = [t['id'] for tl in duplicates.values() for t in tl]
            to_delete  = [tid for tid in all_ids if tid not in tasks_to_keep]

            st.markdown('---')
            col1, col2, col3 = st.columns(3)
            col1.metric('Total de duplicatas', len(all_ids))
            col2.metric('Manter', len(tasks_to_keep))
            col3.metric('Excluir', len(to_delete))

            if to_delete:
                st.markdown('---')
                st.warning(f'⚠️ {len(to_delete)} tarefa(s) serão movidas para a lixeira. Esta ação não pode ser desfeita!')
                _, col_conf, _ = st.columns([1, 2, 1])
                with col_conf:
                    if st.checkbox('Confirmo a exclusão', key='confirm_delete'):
                        if st.button('🗑️ Excluir tarefas selecionadas', use_container_width=True, type='primary'):
                            progress_bar = st.progress(0)
                            status_text  = st.empty()
                            success_count = already_count = error_count = 0
                            errors = []

                            for idx, tid in enumerate(to_delete, 1):
                                status_text.text(f'Excluindo {idx}/{len(to_delete)}...')
                                progress_bar.progress(idx / len(to_delete))
                                ok, msg = delete_meistertask_task(tid, api_token)
                                if ok:
                                    if '404' in msg or 'já estava' in msg:
                                        already_count += 1
                                    else:
                                        success_count += 1
                                else:
                                    error_count += 1
                                    errors.append(msg)
                                time.sleep(0.3)

                            progress_bar.empty()
                            status_text.empty()

                            col1, col2, col3 = st.columns(3)
                            col1.metric('✅ Excluídas', success_count)
                            col2.metric('⚠️ Já excluídas', already_count)
                            col3.metric('❌ Erros', error_count)

                            if error_count == 0:
                                st.balloons()
                                st.success('Concluído sem erros!')
                            else:
                                for e in errors: st.code(e)

                            st.session_state.found_duplicates = None
                            st.session_state.found_tasks = None
            else:
                st.info('✅ Todas as duplicatas estão marcadas para manter.')

        elif st.session_state.found_tasks is not None:
            st.success('✅ Nenhuma duplicata encontrada!')
            st.balloons()

# Footer
st.markdown('---')
st.caption('📧 Sistema de Automação Gmail → MeisterTask')
