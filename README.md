# Gmail → MeisterTask Automation Dashboard

Sistema de automação para processar emails do Gmail com publicações judiciais e criar tarefas no MeisterTask.

## 🚀 Instalação

```bash
git clone https://github.com/SEU_USUARIO/gmail-meistertask-automation.git
cd gmail-meistertask-automation
pip install -r requirements.txt
cp .env.example .env
streamlit run dashboard.py
```

## 📋 Funcionalidades

- Filtrar emails do Gmail
- Extrair publicações judiciais
- Validar cada publicação  
- Criar tarefas no MeisterTask formato [processo] - [partes]

## 🔧 Configuração

Configure o arquivo .env com suas credenciais do Gmail e MeisterTask.
