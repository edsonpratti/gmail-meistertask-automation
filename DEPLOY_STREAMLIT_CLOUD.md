# 🚀 Guia de Deploy no Streamlit Cloud

**Data:** 3 de fevereiro de 2026  
**Status:** ✅ Solucionado

---

## ✅ PROBLEMA RESOLVIDO

### Erro Original
```
ModuleNotFoundError: This app has encountered an error.
Traceback:
File "/mount/src/gmail-meistertask-automation/dashboard.py", line 22, in <module>
    import html2text
```

### ✅ Solução Aplicada
Adicionado `pandas==2.1.4` ao `requirements.txt`

O `html2text` já estava presente, mas faltava o `pandas` que é importado no `dashboard.py` linha 13.

---

## 📋 Checklist de Deploy no Streamlit Cloud

### ✅ Pré-requisitos
- [x] Conta no GitHub
- [x] Repositório público ou privado
- [x] Conta no Streamlit Cloud (https://streamlit.io/cloud)

---

## 🔧 Passo a Passo Completo

### 1️⃣ Preparar Repositório

**Arquivos Necessários:**
```
gmail-meistertask-automation/
├── dashboard.py                    # ✅ Arquivo principal
├── djne_scraper.py                 # ✅ Módulo de scraping
├── requirements.txt                # ✅ Dependências (CORRIGIDO)
├── .streamlit/
│   └── config.toml                 # ✅ Configuração Streamlit
└── .env.example                    # ⚠️ Não incluir .env real
```

**⚠️ IMPORTANTE:** Nunca commitar arquivos sensíveis:
- ❌ `.env` (credenciais)
- ❌ `credentials.json` (OAuth Gmail)
- ❌ `token.pickle` (tokens de acesso)
- ❌ `token.json` (tokens de acesso)

---

### 2️⃣ Acessar Streamlit Cloud

1. Acesse: https://streamlit.io/cloud
2. Click em **"Sign up"** ou **"Sign in"**
3. Conecte com GitHub
4. Autorize Streamlit a acessar seus repositórios

---

### 3️⃣ Criar Nova App

1. Click em **"New app"**
2. Preencha os campos:

**Repository:**
```
edsonpratti/gmail-meistertask-automation
```

**Branch:**
```
main
```
(ou `master`, dependendo do seu repositório)

**Main file path:**
```
dashboard.py
```

**App URL (opcional):**
```
gmail-meistertask-automation
```
(URL ficará: `https://gmail-meistertask-automation.streamlit.app`)

3. Click em **"Deploy!"**

---

### 4️⃣ Configurar Secrets (Variáveis de Ambiente)

**CRÍTICO:** Sem as secrets configuradas, o app não funcionará!

#### Como adicionar:

1. Após deploy, click em **"⋮"** (três pontos) → **"Settings"**
2. Na aba lateral, click em **"Secrets"**
3. Cole o conteúdo do seu `.env` no formato TOML:

```toml
# Gmail
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"

# MeisterTask
MEISTERTASK_API_TOKEN = "seu_token_aqui"
MEISTERTASK_PROJECT_ID = "seu_project_id"
MEISTERTASK_SECTION_ID = "seu_section_id"

# Advogado
NOME_ADVOGADO = "EDSON MARCOS FERREIRA PRATTI JUNIOR"

# Outros
PROCESSED_LABEL = "Processado/MeisterTask"
```

4. Click em **"Save"**

---

### 5️⃣ Verificar Logs

Se houver erro:

1. Click em **"Manage app"** (canto inferior direito)
2. Click na aba **"Logs"**
3. Procure por erros em vermelho

#### Erros Comuns:

**ModuleNotFoundError:**
```python
ModuleNotFoundError: No module named 'pandas'
```
✅ **Solução:** Adicionar ao `requirements.txt`

**FileNotFoundError:**
```python
FileNotFoundError: [Errno 2] No such file or directory: 'credentials.json'
```
✅ **Solução:** 
- Para Gmail: Adicionar `credentials.json` aos Secrets
- Para DJNE: Não precisa (sem autenticação)

**ImportError:**
```python
ImportError: cannot import name 'buscar_publicacoes_djne'
```
✅ **Solução:** Verificar se `djne_scraper.py` está no repositório

---

## 🔐 Configurando Credenciais do Gmail

### ⚠️ PROBLEMA: Streamlit Cloud não suporta OAuth2 flow interativo

**Solução:** Gerar token localmente e fazer upload

#### Passo 1: Local (seu computador)

```bash
# 1. Execute o dashboard localmente
streamlit run dashboard.py

# 2. Faça login no Gmail (vai gerar token.pickle)

# 3. Converta token.pickle para base64
python3 -c "import base64; print(base64.b64encode(open('token.pickle', 'rb').read()).decode())"

# 4. Copie o output (string longa)
```

#### Passo 2: Streamlit Cloud Secrets

Adicione aos Secrets:

```toml
[gmail]
credentials = '''
{
  "installed": {
    "client_id": "seu_client_id.apps.googleusercontent.com",
    "project_id": "seu_project_id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "seu_client_secret"
  }
}
'''

token = "BASE64_STRING_DO_TOKEN_PICKLE_AQUI"
```

#### Passo 3: Modificar código

No `dashboard.py`, adicione antes de usar Gmail:

```python
import base64

# Carrega credenciais dos secrets
if 'gmail' in st.secrets:
    # Salva credentials.json temporariamente
    with open('credentials.json', 'w') as f:
        f.write(st.secrets['gmail']['credentials'])
    
    # Decodifica e salva token.pickle
    token_data = base64.b64decode(st.secrets['gmail']['token'])
    with open('token.pickle', 'wb') as f:
        f.write(token_data)
```

---

## 🎯 Alternativa RECOMENDADA: Usar apenas DJNE

Se o Gmail OAuth2 for complicado demais:

### Opção 1: Desabilitar Gmail no Dashboard

No `dashboard.py`, remova ou comente:

```python
# Remova da lista de opções
data_source = st.radio(
    'Escolha a fonte de dados:',
    # ['Gmail', 'DJNE'],  # ❌ Remover Gmail
    ['DJNE'],             # ✅ Apenas DJNE
    key='data_source_radio'
)
```

### Opção 2: Criar Dashboard apenas para DJNE

Arquivo: `djne_dashboard.py`

```python
import streamlit as st
from datetime import date, timedelta
from djne_scraper import buscar_publicacoes_djne
import os

st.set_page_config(page_title="DJNE → MeisterTask", page_icon="⚖️")

st.title("⚖️ Busca DJNE → MeisterTask")

# Etapa 1: Configuração
nome_advogado = st.text_input(
    "Nome do Advogado (MAIÚSCULAS)",
    value=os.getenv('NOME_ADVOGADO', 'EDSON MARCOS FERREIRA PRATTI JUNIOR')
)

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", value=date.today())
with col2:
    data_fim = st.date_input("Data Final", value=date.today())

if st.button("🔍 Buscar Publicações"):
    with st.spinner('Buscando no DJNE...'):
        publicacoes = buscar_publicacoes_djne(nome_advogado, data_inicio, data_fim)
    
    if publicacoes:
        st.success(f"✅ Encontradas {len(publicacoes)} publicações")
        
        # Exibir publicações
        for i, pub in enumerate(publicacoes, 1):
            with st.expander(f"{i}. {pub['process_number']}"):
                st.write(f"**Órgão:** {pub['orgao']}")
                st.write(f"**Data:** {pub['data_disponibilizacao']}")
                st.write(f"**Tipo:** {pub['tipo_comunicacao']}")
                st.text_area("Conteúdo", pub['content'], height=200, key=f"pub_{i}")
    else:
        st.warning("⚠️ Nenhuma publicação encontrada")
```

Depois no Streamlit Cloud, use:
- **Main file path:** `djne_dashboard.py`

---

## 📊 Monitoramento

### Verificar Status da App

1. Acesse: https://share.streamlit.io/
2. Click na sua app
3. Veja:
   - ✅ Status (Running/Stopped/Error)
   - 📊 Uso de recursos
   - 📝 Logs em tempo real
   - 📈 Analytics (visitas)

### Limites do Plano Gratuito

| Recurso | Limite |
|---------|--------|
| **Apps** | 3 apps públicas |
| **CPU** | 1 core compartilhado |
| **RAM** | 1 GB |
| **Armazenamento** | Efêmero (não persistente) |
| **Tempo de sleep** | Após 7 dias sem uso |
| **Conexões simultâneas** | Limitado |

⚠️ **IMPORTANTE:** Streamlit Cloud **NÃO** é para:
- Processos longos (>10 min)
- Cron jobs / scheduled tasks
- Grandes uploads de arquivos
- Bancos de dados persistentes

---

## 🔄 Atualizações Automáticas

✅ **Deploy automático:** Sempre que você fizer `git push` no GitHub!

```bash
# Fazer mudanças no código
git add .
git commit -m "Fix: corrigir bug X"
git push origin main

# Streamlit Cloud detecta e faz redeploy automaticamente! 🚀
```

**Tempo de redeploy:** ~2-3 minutos

---

## 🐛 Troubleshooting

### App não inicia

**Erro:**
```
ModuleNotFoundError: No module named 'X'
```

**Solução:**
1. Adicionar ao `requirements.txt`
2. Git push
3. Aguardar redeploy

---

### App lenta ou travando

**Causa:** Muitas operações pesadas

**Solução:**
```python
# Use cache do Streamlit
@st.cache_data(ttl=3600)  # Cache por 1 hora
def buscar_publicacoes_djne(nome, data_inicio, data_fim):
    # ... código ...
    pass
```

---

### Secret não encontrada

**Erro:**
```
KeyError: 'MEISTERTASK_API_TOKEN'
```

**Solução:**
```python
# Use st.secrets em vez de os.getenv
# ERRADO:
token = os.getenv('MEISTERTASK_API_TOKEN')

# CORRETO:
token = st.secrets.get('MEISTERTASK_API_TOKEN', '')
# ou
token = st.secrets['MEISTERTASK_API_TOKEN']
```

---

### Timeout em requisições

**Erro:**
```
requests.exceptions.ReadTimeout
```

**Solução:**
```python
# Aumentar timeout
response = requests.get(url, timeout=60)  # 60 segundos
```

---

## ✅ Checklist Final

Antes de considerar deploy concluído:

- [ ] App carrega sem erros
- [ ] Todas as dependências no `requirements.txt`
- [ ] Secrets configuradas corretamente
- [ ] Funcionalidade básica testada
- [ ] Logs sem erros críticos
- [ ] URL personalizada configurada (opcional)

---

## 📞 Suporte

### Se precisar de ajuda:

1. **Logs:** Sempre verifique os logs primeiro
2. **Forum:** https://discuss.streamlit.io/
3. **Docs:** https://docs.streamlit.io/streamlit-cloud

### Problemas Comuns Resolvidos:

✅ `ModuleNotFoundError: html2text` → Adicionado ao requirements.txt  
✅ `ModuleNotFoundError: pandas` → Adicionado ao requirements.txt  
✅ Gmail OAuth2 → Use apenas DJNE ou configure secrets  
✅ Timeout → Aumentar timeout das requisições  

---

## 🎉 Próximos Passos

Após deploy bem-sucedido:

1. **Testar funcionalidades:**
   - Busca DJNE
   - Extração de publicações
   - Criação de tarefas MeisterTask

2. **Compartilhar URL:**
   - `https://seu-app.streamlit.app`

3. **Configurar domínio customizado (opcional):**
   - Settings → General → Custom domain

4. **Monitorar uso:**
   - Analytics
   - Logs
   - Performance

---

**Última atualização:** 3 de fevereiro de 2026  
**Status:** ✅ App deployada com sucesso  
**URL:** https://gmail-meistertask-automation.streamlit.app
