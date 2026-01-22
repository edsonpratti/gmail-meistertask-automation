#!/usr/bin/env python3
"""
Script para adicionar funcionalidade de gerenciamento de duplicatas ao dashboard.py
"""

def main():
    # Lê o arquivo atual
    with open('dashboard.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontra onde adicionar os novos códigos
    new_lines = []
    added_app_mode = False
    added_tasks_to_delete = False
    added_functions = False
    added_sidebar = False
    added_duplicate_mode = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 1. Adiciona app_mode após current_step
        if not added_app_mode and "if 'current_step' not in st.session_state:" in line:
            new_lines.append(line)
            new_lines.append(lines[i+1])  # st.session_state.current_step = 1
            new_lines.append('\n')
            new_lines.append("if 'app_mode' not in st.session_state:\n")
            new_lines.append("    st.session_state.app_mode = 'criar_tarefas'  # 'criar_tarefas' ou 'gerenciar_duplicatas'\n")
            new_lines.append('\n')
            added_app_mode = True
            i += 2
            continue
        
        # 2. Adiciona tasks_to_delete após task_creation_results
        if not added_tasks_to_delete and "if 'task_creation_results' not in st.session_state:" in line:
            new_lines.append(line)
            new_lines.append(lines[i+1])  # st.session_state.task_creation_results = None
            new_lines.append('\n')
            new_lines.append("if 'tasks_to_delete' not in st.session_state:\n")
            new_lines.append("    st.session_state.tasks_to_delete = []\n")
            new_lines.append('\n')
            added_tasks_to_delete = True
            i += 2
            continue
        
        # 3. Adiciona novas funções após create_meistertask_task
        if not added_functions and "def create_meistertask_task" in line:
            # Encontra o fim da função create_meistertask_task
            function_lines = [line]
            i += 1
            while i < len(lines) and not (lines[i].startswith('def ') or lines[i].startswith('# =')):
                function_lines.append(lines[i])
                i += 1
            
            # Adiciona a função original
            new_lines.extend(function_lines)
            new_lines.append('\n\n')
            
            # Adiciona as novas funções
            new_lines.append('''def list_meistertask_tasks(section_id, api_token):
    """
    Lista todas as tarefas de uma seção do MeisterTask
    """
    url = f"https://www.meistertask.com/api/sections/{section_id}/tasks"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            error_detail = f"Status {response.status_code}: {response.text}"
            return False, error_detail
            
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"


def delete_meistertask_task(task_id, api_token):
    """
    Exclui uma tarefa do MeisterTask
    """
    url = f"https://www.meistertask.com/api/tasks/{task_id}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        
        # MeisterTask retorna 204 (No Content) para sucesso na exclusão
        if response.status_code in [200, 204]:
            return True, "Tarefa excluída com sucesso"
        else:
            error_detail = f"Status {response.status_code}: {response.text}"
            return False, error_detail
            
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"


def extract_process_number(task_name):
    """
    Extrai o número do processo do nome da tarefa.
    Formato esperado: "XXXXXXX-XX.XXXX.X.XX.XXXX - Nome das Partes"
    """
    import re
    # Padrão para número de processo brasileiro
    pattern = r'(\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4})'
    match = re.search(pattern, task_name)
    if match:
        return match.group(1)
    return None


def find_duplicate_tasks(tasks):
    """
    Identifica tarefas duplicadas baseadas no número do processo
    Retorna um dicionário: {numero_processo: [lista de tarefas]}
    """
    process_dict = {}
    
    for task in tasks:
        task_name = task.get('name', '')
        process_number = extract_process_number(task_name)
        
        if process_number:
            if process_number not in process_dict:
                process_dict[process_number] = []
            process_dict[process_number].append(task)
    
    # Filtra apenas processos com duplicatas
    duplicates = {k: v for k, v in process_dict.items() if len(v) > 1}
    
    return duplicates

''')
            added_functions = True
            continue
        
        new_lines.append(line)
        i += 1
    
    # Salva arquivo
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✅ Funções adicionadas com sucesso!")
    print(f"Total de linhas: {len(new_lines)}")

if __name__ == '__main__':
    main()
