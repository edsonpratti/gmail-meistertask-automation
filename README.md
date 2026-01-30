# Gmail → MeisterTask Automation Dashboard

Sistema de automação para processar emails do Gmail e publicações do DJNE (Diário de Justiça Eletrônico Nacional), criando tarefas no MeisterTask.

## 🚀 Início Rápido

### Iniciar o Sistema (RECOMENDADO)

```bash
cd ~/Documents/gmail-meistertask-automation
./start.sh
```

O sistema irá:
- ✅ Parar processos antigos automaticamente
- ✅ Liberar a porta 8501
- ✅ Iniciar o dashboard
- ✅ Abrir automaticamente no navegador
- ✅ Exibir: **http://localhost:8501**

### Parar o Sistema

```bash
./stop.sh
```

## 📦 Instalação (Primeira vez)

```bash
git clone https://github.com/edsonpratti/gmail-meistertask-automation.git
cd gmail-meistertask-automation
pip install -r requirements.txt
cp .env.example .env
# Edite o .env com suas credenciais
./start.sh
```

## 📋 Funcionalidades

### Fontes de Dados
- 📧 **Gmail**: Busca emails da caixa de entrada
- ⚖️ **DJNE**: Busca publicações do Diário de Justiça Eletrônico Nacional

### Fluxo de Trabalho
1. **Filtrar** - Escolha a fonte (Gmail ou DJNE) e configure filtros
2. **Selecionar** - Visualize e selecione as publicações
3. **Validar** - Revise o conteúdo de cada publicação
4. **Gerar Tarefas** - Crie tarefas no MeisterTask automaticamente

## 🔧 Configuração

Configure o arquivo `.env` com suas credenciais:

```bash
# Gmail (não precisa editar se já configurado)
# Use credentials.json do Google Cloud Console

# MeisterTask
MEISTERTASK_API_TOKEN=seu_token_aqui
MEISTERTASK_PROJECT_ID=seu_projeto_id
MEISTERTASK_SECTION_ID=sua_secao_id

# OpenAI (opcional, para extração de texto)
OPENAI_API_KEY=sua_chave_aqui

# DJNE (para busca no Diário de Justiça)
DJNE_NOME_ADVOGADO=NOME COMPLETO EM MAIÚSCULAS
```

## ⚠️ Solução de Problemas

### "localhost não funciona" ou "porta ocupada"

**Solução definitiva:**
```bash
./start.sh
```

O script `start.sh` resolve automaticamente todos os problemas de porta e processos antigos.

### Verificar se está rodando

```bash
curl http://localhost:8501
```

Se retornar HTML, está funcionando! Acesse no navegador.

## 📱 Acesso

Após executar `./start.sh`, o sistema estará disponível em:

**http://localhost:8501**

💡 **Dica**: Salve este link nos favoritos do seu navegador!
