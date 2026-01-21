# Como copiar as credenciais do Google Cloud

## Opção 1: Copiar JSON completo

1. No Google Cloud Console, vá em **APIs e Serviços** > **Credenciais**
2. Localize o "ID do cliente OAuth 2.0" que você criou
3. Clique no ícone de **download** (seta para baixo) à direita
4. O arquivo será baixado - se não conseguir, vá para Opção 2

## Opção 2: Copiar dados manualmente

1. No Google Cloud Console, vá em **APIs e Serviços** > **Credenciais**
2. Clique no nome do seu "ID do cliente OAuth 2.0"
3. Na página que abrir, você verá:
   - **ID do cliente** (algo como: xxxxx.apps.googleusercontent.com)
   - **Chave secreta do cliente** (uma string alfanumérica)
   
4. **COPIE ESSES DOIS VALORES** e cole aqui no chat assim:

```
ID do cliente: cole_aqui
Chave secreta: cole_aqui
```

Eu vou criar o arquivo credentials.json automaticamente para você!
