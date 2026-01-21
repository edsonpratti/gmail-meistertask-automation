# 📧 Configuração da Autenticação Gmail

## Passo 1: Criar Projeto no Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Crie um novo projeto ou selecione um existente
3. No nome do projeto, use algo como "Gmail MeisterTask Automation"

## Passo 2: Habilitar Gmail API

1. No menu lateral, vá em **APIs e Serviços** > **Biblioteca**
2. Procure por "Gmail API"
3. Clique em **ATIVAR**

## Passo 3: Criar Credenciais OAuth 2.0

1. Vá em **APIs e Serviços** > **Credenciais**
2. Clique em **+ CRIAR CREDENCIAIS**
3. Selecione **ID do cliente OAuth**
4. Se aparecer aviso sobre tela de consentimento:
   - Clique em **CONFIGURAR TELA DE CONSENTIMENTO**
   - Escolha **Externo** e clique em **CRIAR**
   - Preencha:
     - Nome do app: Gmail MeisterTask
     - Email de suporte: seu email
     - Email do desenvolvedor: seu email
   - Clique em **SALVAR E CONTINUAR** até o final

5. Volte para **Credenciais** > **+ CRIAR CREDENCIAIS** > **ID do cliente OAuth**
6. Tipo de aplicativo: **Aplicativo para computador**
7. Nome: Gmail Desktop Client
8. Clique em **CRIAR**

## Passo 4: Baixar credentials.json

1. Após criar, aparecerá uma janela com as credenciais
2. Clique em **FAZER DOWNLOAD DO JSON**
3. Renomeie o arquivo baixado para `credentials.json`
4. Mova o arquivo para a pasta do projeto:
   ```
   ~/Documents/gmail-meistertask-automation/
   ```

## Passo 5: Executar o Sistema

Após colocar o `credentials.json` na pasta, execute:

```bash
cd ~/Documents/gmail-meistertask-automation
streamlit run dashboard.py
```

Na primeira vez, o navegador abrirá automaticamente para você autorizar o acesso ao Gmail.

## ⚠️ Importante

- O arquivo `credentials.json` contém informações sensíveis
- Nunca compartilhe este arquivo publicamente
- Ele já está no `.gitignore` para não ser enviado ao GitHub

## 🔍 Verificar se está correto

O arquivo `credentials.json` deve ter esta estrutura:

```json
{
  "installed": {
    "client_id": "seu-client-id.apps.googleusercontent.com",
    "project_id": "seu-projeto",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    ...
  }
}
```

## 🚀 Próximos Passos

Depois de configurar o Gmail, você também precisará configurar:
- Token da API do MeisterTask
- Chave da API do OpenAI

Edite o arquivo `.env` com essas informações.
