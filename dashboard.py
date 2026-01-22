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
if st.session_state.current_step > 1 and not st.session_state.filtered_emails:
    st.session_state.current_step = 1
if st.session_state.current_step > 2 and not st.session_state.selected_email_ids:
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
    Testa múltiplos padrões para encontrar as separações
    """
    publications = []
    
    # DEBUG: Mostra amostra do email
    st.info(f"📝 Primeiros 500 caracteres do email:\n{email_body[:500]}")
    
    # Testa vários padrões possíveis em ordem de especificidade
    patterns_to_try = [
        (r'Publicação:\s*\d+\.\s+', 'Publicação: N. (com ponto e espaços)'),
        (r'Publicação:\s*\d+\.', 'Publicação: N. (com ponto)'),
        (r'Publicação:\s*\d+', 'Publicação: N (sem ponto)'),
        (r'Publicação:', 'Publicação: (genérico)')
    ]
    
    pub_matches = None
    pattern_used = None
    
    for pattern, description in patterns_to_try:
        matches = list(re.finditer(pattern, email_body, re.IGNORECASE))
        if matches:
            pub_matches = matches
            pattern_used = description
            st.info(f"🔍 Usando padrão: {description} - Encontradas {len(matches)} ocorrências")
            break
    
    if not pub_matches:
        st.warning("⚠️ Nenhum padrão de 'Publicação' encontrado. Tratando email como uma única publicação.")
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
        
        # Tenta extrair número do processo (padrão brasileiro)
        process_pattern = r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})'
        process_match = re.search(process_pattern, pub_content)
        process_number = process_match.group(0) if process_match else f'Publicação {i+1}'
        
        publications.append({
            'process_number': process_number,
            'content': pub_content,
            'source_subject': email_subject
        })
    
    st.success(f"✅ Extraídas {len(publications)} publicações usando padrão: {pattern_used}")
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
                
                # Debug: mostra quantas tarefas vieram nesta página
                st.info(f"📄 Página {page}: {len(tasks)} tarefas recuperadas (offset: {offset})")
                
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
                    st.warning("⚠️ Limite de páginas atingido. Se houver mais tarefas, elas não foram carregadas.")
                    break
                
            else:
                error_detail = f"Status {response.status_code}: {response.text}"
                return False, error_detail
        
        st.success(f"✅ Total de tarefas carregadas: {len(all_tasks)} (de {page} página(s))")
        return True, all_tasks
            
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"


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
        else:
            return False, f"Status {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"


def delete_meistertask_task(task_id, api_token):
    """
    Move uma tarefa do MeisterTask para a lixeira (trash)
    A API do MeisterTask usa PUT com status=18 para enviar tarefas para a lixeira
    """
    # Primeiro verifica se a tarefa existe
    success, task_data = get_meistertask_task(task_id, api_token)
    if not success:
        return False, f"Não foi possível verificar a tarefa antes de deletar: {task_data}"
    
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
            # Verifica a resposta para debug
            if response.status_code == 200:
                result = response.json()
                new_status = result.get('status', 'unknown')
                return True, f"Tarefa movida para lixeira (novo status: {new_status})"
            return True, "Tarefa movida para lixeira com sucesso"
        elif response.status_code == 400:
            # Se status=18 não funcionar, tenta outros valores conhecidos
            # Status 2 = Completa, pode precisar disso antes
            error_msg = response.text[:200] if len(response.text) > 200 else response.text
            return False, f"Não foi possível mover para lixeira. Resposta da API: {error_msg}"
        elif response.status_code == 403:
            return False, "Sem permissão para deletar esta tarefa"
        elif response.status_code == 404:
            return False, "Tarefa não encontrada"
        else:
            error_msg = response.text[:300] if len(response.text) > 300 else response.text
            return False, f"Erro ao deletar (status {response.status_code}): {error_msg}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"


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
        st.info(f"🔍 Filtro aplicado: {len(filtered_tasks)} tarefas sem responsável (de {len(tasks)} totais)")
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
    
    # Debug detalhado
    st.info(f"📊 Estatísticas:")
    st.write(f"- Total de tarefas analisadas: **{len(filtered_tasks)}**")
    st.write(f"- Tarefas com número de processo válido: **{len(seen_task_ids)}**")
    st.write(f"- Tarefas sem número de processo: **{len(tasks_without_process)}**")
    st.write(f"- Processos únicos encontrados: **{len(process_dict)}**")
    st.write(f"- Processos com duplicatas (2+ tarefas): **{len(duplicates)}**")
    
    if tasks_without_process:
        with st.expander("⚠️ Ver tarefas sem número de processo (não serão processadas)"):
            for t in tasks_without_process[:10]:  # Mostra primeiras 10
                st.text(f"- {t}")
            if len(tasks_without_process) > 10:
                st.text(f"... e mais {len(tasks_without_process) - 10} tarefas")
    
    return duplicates

# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================

st.title("📧 Sistema de Automação Gmail → MeisterTask")
st.markdown("**Validação Manual em Múltiplas Etapas**")

# Sidebar - Navegação e Status
with st.sidebar:
    st.header("🎯 Modo de Operação")
    
    mode = st.radio(
        "Escolha o que deseja fazer:",
        options=['criar_tarefas', 'gerenciar_duplicatas'],
        format_func=lambda x: '➕ Criar Novas Tarefas' if x == 'criar_tarefas' else '🔍 Gerenciar Duplicatas',
        index=0 if st.session_state.app_mode == 'criar_tarefas' else 1,
        key='mode_selector'
    )
    
    # Se mudou o modo, atualiza e reinicia
    if mode != st.session_state.app_mode:
        st.session_state.app_mode = mode
        st.session_state.current_step = 1
        st.session_state.tasks_to_delete = []
        st.rerun()
    
    st.markdown("---")
    
    if st.session_state.app_mode == 'criar_tarefas':
        st.header("📍 Etapas do Processo")
        
        # Indicador visual de progresso
        steps = [
            ("1️⃣", "Filtrar Emails", 1),
            ("2️⃣", "Selecionar Emails", 2),
            ("3️⃣", "Validar Publicações", 3),
            ("4️⃣", "Gerar Tarefas", 4)
        ]
        
        for icon, name, step_num in steps:
            if st.session_state.current_step == step_num:
                st.markdown(f"**{icon} {name}** ✓")
            elif st.session_state.current_step > step_num:
                st.markdown(f"~~{icon} {name}~~ ✅")
            else:
                st.markdown(f"{icon} {name}")
        
        st.markdown("---")
    
    # Status do Gmail
    st.header("📊 Status")
    gmail_connected = os.path.exists('token.pickle')
    st.metric("Gmail", "✅ Conectado" if gmail_connected else "❌ Desconectado")
    
    if not gmail_connected:
        st.warning("⚠️ Execute autenticação do Gmail primeiro")
    
    st.markdown("---")
    
    # Botões de navegação
    st.header("🎮 Controles")
    
    if st.button("🔄 Reiniciar Processo", use_container_width=True, key="sidebar_reset"):
        st.session_state.current_step = 1
        st.session_state.filtered_emails = []
        st.session_state.selected_email_ids = []
        st.session_state.extracted_publications = []
        st.session_state.selected_publication_ids = []
        st.session_state.task_creation_results = None
        st.session_state.tasks_to_delete = []
        st.rerun()

st.markdown("---")

# =============================================================================
# ETAPA 1: FILTRAR EMAILS
# =============================================================================

if st.session_state.current_step == 1:
    st.header("1️⃣ Buscar Publicações")
    
    # Escolha da fonte de dados
    st.subheader("📊 Fonte de Dados")
    fonte = st.radio(
        "Escolha onde buscar as publicações:",
        options=['Gmail', 'DJNE'],
        horizontal=True,
        help="Gmail: busca em emails recebidos | DJNE: busca direta no Diário de Justiça Eletrônico Nacional"
    )
    st.session_state.fonte_dados = fonte
    
    st.markdown("---")
    
    # Filtros baseados na fonte escolhida
    if fonte == 'Gmail':
        st.subheader("🔍 Filtros de Email")
    else:
        st.subheader("🔍 Filtros de Busca DJNE")
    
    col1, col2, col3 = st.columns(3)
    
    if fonte == 'Gmail':
        with col1:
            st.subheader("🔍 Texto")
            text_search = st.text_input(
                "Buscar no assunto ou corpo",
                value=st.session_state.filters.get('text_search', ''),
                placeholder="Ex: intimação, publicação, processo"
            )
        
        with col2:
            st.subheader("📅 Data de Recebimento")
            date_from = st.date_input(
                "De:",
                value=st.session_state.filters.get('date_from') or (datetime.now() - timedelta(days=7)).date()
            )
            date_to = st.date_input(
                "Até:",
                value=st.session_state.filters.get('date_to') or datetime.now().date()
            )
        
        with col3:
            st.subheader("📬 Status")
            read_status = st.radio(
                "Mostrar emails:",
                options=['unread', 'read', 'all'],
                format_func=lambda x: {
                    'unread': '📭 Não lidos',
                    'read': '📬 Lidos',
                    'all': '📧 Todos'
                }[x],
                index=['unread', 'read', 'all'].index(st.session_state.filters.get('read_status', 'unread'))
            )
    else:  # DJNE
        text_search = ''
        read_status = 'all'
        
        with col1:
            st.info(f"👤 **Advogado:** {load_env_var('DJNE_NOME_ADVOGADO', 'EDSON MARCOS FERREIRA PRATTI JUNIOR')}")
        
        with col2:
            st.subheader("📅 Data da Publicação")
            date_from = st.date_input(
                "De:",
                value=st.session_state.filters.get('date_from') or datetime.now().date()
            )
            date_to = st.date_input(
                "Até:",
                value=st.session_state.filters.get('date_to') or datetime.now().date()
            )
        
        with col3:
            st.info("ℹ️ A busca será feita diretamente no site do DJNE")
    
    st.markdown("---")
    
    # Botão Aplicar Filtros
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        btn_text = "🔍 BUSCAR NO GMAIL" if fonte == 'Gmail' else "🔍 BUSCAR NO DJNE"
        if st.button(btn_text, use_container_width=True, type="primary"):
            # Atualiza filtros (armazena datas como objetos date, não strings)
            st.session_state.filters = {
                'text_search': text_search,
                'date_from': date_from,
                'date_to': date_to,
                'read_status': read_status
            }
            
            if fonte == 'Gmail':
                # Busca emails no Gmail
                with st.spinner("Buscando emails no Gmail..."):
                    gmail_service = get_gmail_service()
                    if gmail_service:
                        emails = search_emails(gmail_service, st.session_state.filters)
                        st.session_state.filtered_emails = emails
                        
                        if emails:
                            st.success(f"✅ {len(emails)} emails encontrados!")
                            time.sleep(1)
                            st.session_state.current_step = 2
                            st.rerun()
                        else:
                            st.warning("Nenhum email encontrado com esses filtros.")
                    else:
                        st.error("❌ Erro ao conectar com Gmail. Verifique a autenticação.")
            else:  # DJNE
                # Busca publicações no DJNE
                with st.spinner("Buscando publicações no DJNE..."):
                    try:
                        nome_advogado = load_env_var('DJNE_NOME_ADVOGADO', 'EDSON MARCOS FERREIRA PRATTI JUNIOR')
                        publicacoes = buscar_publicacoes_djne(nome_advogado, date_from, date_to)
                        
                        # Converte publicações DJNE para formato compatível com emails
                        # Pula direto para a etapa 3 (publicações já extraídas)
                        for idx, pub in enumerate(publicacoes):
                            pub['email_id'] = f"djne_{idx}"
                            pub['email_subject'] = pub['source_subject']
                            pub['email_sender'] = 'DJNE'
                            pub['email_date'] = pub['data_disponibilizacao']
                            pub['pub_id'] = f"djne_{idx}"
                        
                        st.session_state.extracted_publications = publicacoes
                        
                        if publicacoes:
                            st.success(f"✅ {len(publicacoes)} publicações encontradas no DJNE!")
                            time.sleep(1)
                            st.session_state.current_step = 3  # Pula direto para validação
                            st.rerun()
                        else:
                            st.warning("Nenhuma publicação encontrada no DJNE para este período.")
                    except Exception as e:
                        st.error(f"❌ Erro ao buscar no DJNE: {str(e)}")

# =============================================================================
# ETAPA 2: SELECIONAR EMAILS
# =============================================================================

elif st.session_state.current_step == 2:
    st.header("2️⃣ Selecionar Emails para Processar")
    
    st.info(f"📊 Total encontrado: **{len(st.session_state.filtered_emails)}**")
    
    # Exibir filtros aplicados
    with st.expander("🔍 Filtros Aplicados"):
        filters = st.session_state.filters
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Texto:**", filters.get('text_search') or "Nenhum")
        with col2:
            date_from_str = filters.get('date_from').strftime('%Y/%m/%d') if filters.get('date_from') else 'Início'
            date_to_str = filters.get('date_to').strftime('%Y/%m/%d') if filters.get('date_to') else 'Hoje'
            st.write("**Período:**", f"{date_from_str} até {date_to_str}")
        with col3:
            st.write("**Status:**", {
                'unread': 'Não lidos',
                'read': 'Lidos',
                'all': 'Todos'
            }.get(filters.get('read_status'), 'Não lidos'))
    
    st.markdown("---")
    
    # Lista de emails com preview
    for idx, email in enumerate(st.session_state.filtered_emails):
        with st.expander(
            f"{'✉️' if not email['is_read'] else '📬'} **{email['subject'][:80]}...** - {email['sender'][:50]}",
            expanded=False
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**De:** {email['sender']}")
                st.markdown(f"**Data:** {email['date']}")
                st.markdown(f"**Status:** {'Não lido' if not email['is_read'] else 'Lido'}")
                st.markdown("**Conteúdo:**")
                
                # Mostrar preview do corpo (primeiros 500 caracteres)
                body_preview = email['body'][:500] + "..." if len(email['body']) > 500 else email['body']
                st.text_area(
                    "Corpo do email",
                    value=body_preview,
                    height=200,
                    key=f"body_{email['id']}",
                    disabled=True
                )
                
            with col2:
                # Checkbox para seleção
                is_selected = st.checkbox(
                    "Selecionar",
                    value=email['id'] in st.session_state.selected_email_ids,
                    key=f"select_{email['id']}"
                )
                
                if is_selected and email['id'] not in st.session_state.selected_email_ids:
                    st.session_state.selected_email_ids.append(email['id'])
                elif not is_selected and email['id'] in st.session_state.selected_email_ids:
                    st.session_state.selected_email_ids.remove(email['id'])
    
    st.markdown("---")
    
    # Botões de navegação
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    
    
    with col1:
        if st.button("🏠", use_container_width=True, key="home_step2", help="Voltar ao Início"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.button("⬅️ Voltar aos Filtros", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()
    
    with col3:
        selected_count = len(st.session_state.selected_email_ids)
        if st.button(
            f"📤 EXTRAIR PUBLICAÇÕES ({selected_count} selecionados)",
            use_container_width=True,
            type="primary",
            disabled=selected_count == 0
        ):
            with st.spinner("Extraindo publicações..."):
                publications = []
                
                for email in st.session_state.filtered_emails:
                    if email['id'] in st.session_state.selected_email_ids:
                        # Extrai publicações do email
                        email_pubs = extract_publications_from_email(email['body'], email['subject'])
                        
                        # Adiciona metadados
                        for pub in email_pubs:
                            pub['email_id'] = email['id']
                            pub['email_subject'] = email['subject']
                            pub['email_sender'] = email['sender']
                            pub['email_date'] = email['date']
                            pub['pub_id'] = f"{email['id']}_{len(publications)}"
                            publications.append(pub)
                
                st.session_state.extracted_publications = publications
                
                if publications:
                    st.success(f"✅ {len(publications)} publicações extraídas de {selected_count} emails!")
                    time.sleep(1)
                    st.session_state.current_step = 3
                    st.rerun()
                else:
                    st.warning("Nenhuma publicação encontrada nos emails selecionados.")

# =============================================================================
# ETAPA 3: VALIDAR PUBLICAÇÕES
# =============================================================================

elif st.session_state.current_step == 3:
    st.header("3️⃣ Validar e Selecionar Publicações")
    
    total_pubs = len(st.session_state.extracted_publications)
    st.info(f"📋 Total de publicações extraídas: **{total_pubs}**")
    
    st.markdown("---")
    
    # Exibir publicações
    for idx, pub in enumerate(st.session_state.extracted_publications):
        # Indicador visual: ✅ se selecionado, 📄 se não
        is_selected = pub['pub_id'] in st.session_state.selected_publication_ids
        icon = '✅' if is_selected else '📄'
        with st.expander(
            f"{icon} **Processo: {pub['process_number']}** - Email: {pub['email_subject'][:60]}...",
            expanded=True  # Expandido por padrão
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Número do Processo:** {pub['process_number']}")
                st.markdown(f"**Email de Origem:** {pub['email_subject']}")
                st.markdown(f"**Remetente:** {pub['email_sender']}")
                st.markdown(f"**Data:** {pub['email_date']}")
                
                st.markdown("---")
                st.markdown("**Conteúdo da Publicação:**")
                
                # Mostrar conteúdo completo
                st.text_area(
                    "Texto da publicação",
                    value=pub['content'],
                    height=300,
                    key=f"pub_content_{pub['pub_id']}",
                    disabled=True
                )
            
            with col2:
                # Checkbox para seleção
                is_selected_pub = st.checkbox(
                    "Selecionar para gerar tarefa",
                    value=pub['pub_id'] in st.session_state.selected_publication_ids,
                    key=f"select_pub_{pub['pub_id']}"
                )
                
                if is_selected_pub and pub['pub_id'] not in st.session_state.selected_publication_ids:
                    st.session_state.selected_publication_ids.append(pub['pub_id'])
                elif not is_selected_pub and pub['pub_id'] in st.session_state.selected_publication_ids:
                    st.session_state.selected_publication_ids.remove(pub['pub_id'])
    
    st.markdown("---")
    
    # Botões de navegação
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    
    
    with col1:
        if st.button("🏠", use_container_width=True, key="home_step3", help="Voltar ao Início"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.button("⬅️ Voltar aos Emails", use_container_width=True):
            st.session_state.current_step = 2
            st.rerun()
    
    with col3:
        selected_count = len(st.session_state.selected_publication_ids)
        if st.button(
            f"✅ GERAR TAREFAS ({selected_count} selecionadas)",
            use_container_width=True,
            type="primary",
            disabled=selected_count == 0
        ):
            st.session_state.current_step = 4
            st.rerun()

# =============================================================================
# ETAPA 4: GERAR TAREFAS
# =============================================================================

elif st.session_state.current_step == 4:
    st.header("4️⃣ Gerar Tarefas no MeisterTask")
    
    # Aviso se não há publicações (página recarregada)
    if not st.session_state.selected_publication_ids:
        st.warning("⚠️ Nenhuma publicação selecionada. Você pode ter recarregado a página.")
        st.info("Clique no botão 'Reiniciar Processo' na barra lateral para começar novamente.")
        st.stop()
    
    selected_pubs = [
        pub for pub in st.session_state.extracted_publications
        if pub['pub_id'] in st.session_state.selected_publication_ids
    ]
    
    st.info(f"🎯 **{len(selected_pubs)}** publicações selecionadas para criar tarefas")
    
    st.markdown("---")
    
    # Preview das tarefas que serão criadas
    st.subheader("📋 Preview das Tarefas:")
    
    for idx, pub in enumerate(selected_pubs, 1):
        with st.expander(f"{idx}. {pub['process_number']}", expanded=False):
            # Extrai informações da publicação
            parties = extract_parties_from_publication(pub['content'])
            task_title = f"{pub['process_number']} - {parties}"
            
            st.markdown(f"**Título da Tarefa:**")
            st.code(task_title)
            
            st.markdown(f"**Partes:** {parties}")
            st.markdown(f"**Email de Origem:** {pub['email_subject']}")
            
            # Preview do conteúdo (primeiros 500 caracteres)
            content_preview = pub['content'][:500] + "..." if len(pub['content']) > 500 else pub['content']
            st.text_area(
                "Preview do Conteúdo (Descrição da Tarefa):",
                value=content_preview,
                height=150,
                disabled=True,
                key=f"preview_{idx}"
            )
    
    st.markdown("---")
    
    # Informações de destino
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📁 **Projeto:** Edson Pratti Advogados")
    with col2:
        st.info(f"📌 **Seção:** Publicações")
    
    st.markdown("---")
    
    # Botões de ação
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    
    
    with col1:
        if st.button("🏠", use_container_width=True, key="home_step4", help="Voltar ao Início"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        btn_voltar = st.button("⬅️ Voltar às Publicações", use_container_width=True, key="btn_back_to_pubs")
        if btn_voltar:
            st.session_state.current_step = 3
            st.rerun()
    with col3:
        if st.button(
            f"🚀 CRIAR {len(selected_pubs)} TAREFAS",
            use_container_width=True,
            type="primary"
        ):
            # Carrega configurações do .env
            api_token = load_env_var('MEISTERTASK_API_TOKEN')
            section_id = load_env_var('MEISTERTASK_SECTION_ID')
            
            # Debug: mostra configurações (parcialmente)
            st.info(f"🔑 API Token: {'✅ Configurado' if api_token else '❌ Não encontrado'}")
            st.info(f"📌 Section ID: {section_id if section_id else '❌ Não encontrado'}")
            
            if not api_token or not section_id:
                st.error("❌ Erro: MEISTERTASK_API_TOKEN ou MEISTERTASK_SECTION_ID não configurados no arquivo .env")
                st.stop()
            
            # Container para resultados que não desaparecem
            results_container = st.container()
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            error_count = 0
            errors = []
            success_tasks = []
            
            for idx, pub in enumerate(selected_pubs):
                # Atualiza progresso
                progress = (idx + 1) / len(selected_pubs)
                progress_bar.progress(progress)
                status_text.text(f"Criando tarefa {idx + 1} de {len(selected_pubs)}: {pub['process_number']}")
                
                # Extrai informações
                parties = extract_parties_from_publication(pub['content'])
                
                # Cria tarefa no MeisterTask
                success, result = create_meistertask_task(
                    process_number=pub['process_number'],
                    parties=parties,
                    description=pub['content'],
                    section_id=section_id,
                    api_token=api_token
                )
                
                if success:
                    success_count += 1
                    success_tasks.append(pub['process_number'])
                else:
                    error_count += 1
                    error_msg = f"{pub['process_number']}: {result}"
                    errors.append(error_msg)
                
                time.sleep(0.5)  # Evita rate limiting
            
            # Limpa barra de progresso
            progress_bar.empty()
            status_text.empty()
            
            # Salva resultados no session state para não desaparecerem
            st.session_state.task_creation_results = {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors,
                'success_tasks': success_tasks
            }
    
    # Mostra resultados salvos (persistem na tela)
    if st.session_state.task_creation_results:
        results = st.session_state.task_creation_results
        
        st.markdown("---")
        st.subheader("📊 Resultado da Criação de Tarefas:")
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ **{results['success_count']}** tarefas criadas com sucesso!")
            if results['success_tasks']:
                with st.expander("Ver tarefas criadas"):
                    for task in results['success_tasks']:
                        st.text(f"✓ {task}")
        
        with col2:
            if results['error_count'] > 0:
                st.error(f"❌ **{results['error_count']}** erros")
                with st.expander("⚠️ VER DETALHES DOS ERROS (CLIQUE AQUI)", expanded=True):
                    for error in results['errors']:
                        st.code(error, language=None)
        
        # Botões de navegação após conclusão
        st.markdown("---")
        st.success("🎉 Processo concluído! Use o botão abaixo para iniciar um novo processo.")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🏠 VOLTAR AO INÍCIO", use_container_width=True, type="primary", key="reset_all"):
                # Limpa todos os estados
                for key in ['current_step', 'filtered_emails', 'selected_email_ids', 
                           'extracted_publications', 'selected_publication_ids', 'task_creation_results']:
                    if key in st.session_state:
                        if key == 'current_step':
                            st.session_state[key] = 1
                        else:
                            st.session_state[key] = [] if key != 'task_creation_results' else None
                
                st.success("✅ Sistema reiniciado!")
                time.sleep(0.5)
                st.rerun()

# =============================================================================
# MODO: GERENCIAR DUPLICATAS
# =============================================================================

if st.session_state.app_mode == 'gerenciar_duplicatas':
    st.title("🔍 Gerenciamento de Tarefas Duplicadas")
    st.markdown("Esta ferramenta identifica e permite excluir tarefas duplicadas na seção **Publicações** do MeisterTask.")
    st.markdown("**Critério:** Tarefas com o mesmo número de processo são consideradas duplicatas.")
    
    st.markdown("---")
    
    # Carregar credenciais
    api_token = load_env_var('MEISTERTASK_API_TOKEN')
    section_id = load_env_var('MEISTERTASK_SECTION_ID')
    
    if not api_token or not section_id:
        st.error("❌ Erro: MEISTERTASK_API_TOKEN ou MEISTERTASK_SECTION_ID não configurados no arquivo .env")
        st.stop()
    
    # Botão para buscar tarefas
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Buscar Tarefas da Seção Publicações", use_container_width=True, type="primary"):
            with st.spinner("🔍 Buscando tarefas..."):
                success, result = list_meistertask_tasks(section_id, api_token)
                
                if success:
                    tasks = result
                    st.success(f"✅ {len(tasks)} tarefas encontradas!")
                    
                    # Armazenar no session_state
                    st.session_state.found_tasks = tasks
                    
                    # Identificar duplicatas
                    duplicates = find_duplicate_tasks(tasks)
                    st.session_state.found_duplicates = duplicates
                    
                else:
                    st.error(f"❌ Erro ao buscar tarefas: {result}") 
    
    # Mostrar duplicatas se existirem no session_state
    if st.session_state.found_duplicates:
        duplicates = st.session_state.found_duplicates
        st.warning(f"⚠️ Encontradas {len(duplicates)} processos com tarefas duplicadas!")
        
        # Mostrar duplicatas
        st.markdown("---")
        st.subheader("📋 Tarefas Duplicadas Encontradas")
        st.info("✓ Marque as tarefas que deseja **MANTER** (as desmarcadas serão excluídas)")
        
        # Lista para armazenar IDs das tarefas a manter
        tasks_to_keep = []
        
        for process_idx, (process_num, task_list) in enumerate(duplicates.items()):
            with st.expander(f"📂 Processo: **{process_num}** ({len(task_list)} duplicatas)", expanded=True):
                st.warning(f"⚠️ **ATENÇÃO**: Revise cuidadosamente se estas {len(task_list)} tarefas são REALMENTE duplicatas do mesmo processo!")
                st.markdown(f"**Encontradas {len(task_list)} tarefas para o mesmo processo:**")
                
                # Mostrar cada tarefa duplicada
                for idx, task in enumerate(task_list, 1):
                    task_id = task.get('id')
                    task_name = task.get('name', 'Sem nome')
                    task_created = task.get('created_at', 'Data desconhecida')
                    task_status = task.get('status', 'Sem status')
                    
                    # Cria uma coluna para checkbox e informações
                    col_check, col_info = st.columns([1, 9])
                    
                    with col_check:
                        # Por padrão, marca a primeira tarefa (mais antiga) para manter
                        # Chave única: processo_idx + idx + task_id para garantir unicidade absoluta
                        keep_task = st.checkbox(
                            "Manter",
                            value=(idx == 1),  # Marca primeira por padrão
                            key=f"keep_{process_idx}_{idx}_{task_id}",
                            label_visibility="collapsed"
                        )
                        
                        if keep_task:
                            tasks_to_keep.append(task_id)
                    
                    with col_info:
                        st.markdown(f"""
                        **Tarefa {idx}:**
                        - 📝 **Nome COMPLETO:** `{task_name}`
                        - 🆔 **ID:** {task_id}
                        - 📅 **Criada em:** {task_created[:10] if len(task_created) > 10 else task_created}
                        - 📊 **Status:** {task_status}
                        """)
                
                st.markdown("---")
        
        # Calcular tarefas a excluir
        all_duplicate_ids = [task['id'] for task_list in duplicates.values() for task in task_list]
        tasks_to_delete = [tid for tid in all_duplicate_ids if tid not in tasks_to_keep]
        
        # Mostrar resumo
        st.markdown("---")
        st.subheader("📊 Resumo da Operação")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Duplicatas", len(all_duplicate_ids))
        with col2:
            st.metric("Tarefas a Manter", len(tasks_to_keep), delta=None, delta_color="off")
        with col3:
            st.metric("Tarefas a Excluir", len(tasks_to_delete), delta=f"-{len(tasks_to_delete)}", delta_color="inverse")
        
        # Botão de confirmação para excluir
        if tasks_to_delete:
            st.markdown("---")
            st.warning(f"⚠️ **ATENÇÃO:** Você está prestes a excluir **{len(tasks_to_delete)} tarefas**. Esta ação não pode ser desfeita!")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                confirm_delete = st.checkbox("✅ Confirmo que quero excluir as tarefas desmarcadas", key="confirm_delete")
                
                if confirm_delete:
                    if st.button("🗑️ EXCLUIR TAREFAS SELECIONADAS", use_container_width=True, type="primary"):
                        # Executar exclusão
                        st.markdown("---")
                        st.subheader("🔄 Excluindo Tarefas...")
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        success_count = 0
                        error_count = 0
                        errors = []
                        
                        for idx, task_id in enumerate(tasks_to_delete, 1):
                            status_text.text(f"Excluindo tarefa {idx} de {len(tasks_to_delete)}...")
                            progress_bar.progress(idx / len(tasks_to_delete))
                            
                            success, message = delete_meistertask_task(task_id, api_token)
                            
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                errors.append(f"Tarefa ID {task_id}: {message}")
                            
                            time.sleep(0.3)  # Evita rate limiting
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        # Mostrar resultados
                        st.markdown("---")
                        st.subheader("📊 Resultado da Exclusão")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.success(f"✅ **{success_count}** tarefas excluídas com sucesso!")
                        
                        with col2:
                            if error_count > 0:
                                st.error(f"❌ **{error_count}** erros")
                                with st.expander("Ver erros"):
                                    for error in errors:
                                        st.code(error)
                        
                        st.balloons()
                        st.success("🎉 Processo de limpeza concluído! Clique em 'Reiniciar Processo' para buscar novamente.")
                        
                        # Limpar estado após exclusão
                        st.session_state.found_duplicates = None
                        st.session_state.found_tasks = None
        else:
            st.info("✅ Todas as tarefas duplicadas estão marcadas para manter. Não há nada para excluir.")
    
    elif st.session_state.found_tasks is not None:
        # Buscou tarefas mas não encontrou duplicatas
        st.success("✅ Nenhuma duplicata encontrada! Todas as tarefas têm números de processo únicos.")
        st.balloons()

# Footer
st.markdown("---")
st.caption("📧 Sistema de Automação Gmail → MeisterTask | Desenvolvido com Streamlit")
