# 🔧 Corrigir Erro redirect_uri_mismatch

## Passo a Passo:

1. Acesse: https://console.cloud.google.com/apis/credentials

2. Localize o **ID do cliente OAuth 2.0** que você criou
   - O nome deve ser algo como "Gmail Desktop Client" 
   - Ou começar com: 975303249155-l7c06qjli627tq5duph6khfqc07i39co

3. **CLIQUE** no nome do ID do cliente (não no ícone de download)

4. Na tela que abrir, procure **"URIs de redirecionamento autorizados"**

5. Clique em **"+ ADICIONAR URI"**

6. Cole este URI:
   ```
   http://localhost:8080/
   ```

7. Clique em **SALVAR** no final da página

## ✅ Pronto!

Depois de salvar, volte e recarregue o dashboard (F5).
Quando clicar em "Conectar Gmail", a autorização funcionará!
