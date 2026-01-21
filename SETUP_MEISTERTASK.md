# 🔧 Como Obter as Credenciais do MeisterTask

## Passo 1: Obter o API Token

1. Acesse: https://www.meistertask.com/app
2. Clique no seu **avatar/foto** no canto superior direito
3. Vá em **Configurações** ou **Settings**
4. Procure por **Developer** ou **API**
5. Clique em **Generate New Token** ou **Gerar Novo Token**
6. Copie o token gerado (ele aparece apenas uma vez!)

## Passo 2: Obter o Project ID

1. No MeisterTask, abra o **projeto** onde você quer criar as tarefas
2. Olhe na URL do navegador, ela será algo como:
   ```
   https://www.meistertask.com/app/project/XXXXXXX/board
   ```
3. O número **XXXXXXX** é o seu **Project ID**

## Passo 3: Obter o Section ID

Você tem 2 opções:

### Opção A - Usar o script automático (mais fácil):

Execute este comando no terminal:
```bash
cd ~/Documents/gmail-meistertask-automation
python3 list_sections.py
```

Isso vai listar todas as seções do projeto e seus IDs.

### Opção B - Manualmente via API:

1. Substitua no comando abaixo:
   - `SEU_TOKEN` pelo token obtido no Passo 1
   - `SEU_PROJECT_ID` pelo ID obtido no Passo 2

```bash
curl -X GET "https://www.meistertask.com/api/projects/SEU_PROJECT_ID/sections" \
  -H "Authorization: Bearer SEU_TOKEN"
```

2. O resultado mostrará todas as seções. Escolha o ID da seção desejada.

## Passo 4: Configurar o .env

Cole os valores aqui no chat assim:

```
Token: seu_token_aqui
Project ID: seu_project_id_aqui
Section ID: seu_section_id_aqui
```

Eu vou configurar automaticamente o arquivo .env para você!

## 📌 Exemplo de valores:

```
MEISTERTASK_API_TOKEN=abc123def456ghi789
MEISTERTASK_PROJECT_ID=1234567
MEISTERTASK_SECTION_ID=7654321
```
