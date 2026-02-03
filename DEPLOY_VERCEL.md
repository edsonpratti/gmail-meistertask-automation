# ⚠️ IMPORTANTE: Vercel NÃO é recomendado para Streamlit

## Problema

O **Vercel não suporta aplicações Streamlit** de forma nativa porque:
- Streamlit precisa de servidor persistente (WebSocket)
- Vercel usa funções serverless (sem estado)
- Streamlit requer conexões de longa duração
- Vercel tem timeout de 10s para funções

## ✅ Soluções Recomendadas

### Opção 1: Streamlit Cloud (RECOMENDADO) 🌟

**Melhor opção** - Gratuito e otimizado para Streamlit

#### Passos:
1. Acesse https://streamlit.io/cloud
2. Conecte sua conta GitHub
3. Selecione o repositório `edsonpratti/gmail-meistertask-automation`
4. Configure:
   - **Main file path:** `dashboard.py`
   - **Python version:** 3.9
5. Adicione as variáveis de ambiente (secrets):
   ```
   NOME_ADVOGADO="EDSON MARCOS FERREIRA PRATTI JUNIOR"
   MEISTERTASK_API_TOKEN=seu_token
   MEISTERTASK_SECTION_ID=seu_section_id
   ```
6. Deploy automático!

**URL resultante:** `https://seu-app.streamlit.app`

---

### Opção 2: Render.com (GRATUITO) 🎯

**Já configurado** - Arquivo `render.yaml` está pronto

#### Passos:
1. Acesse https://render.com
2. Crie uma conta
3. New → Web Service
4. Conecte o repositório GitHub
5. Render detecta automaticamente o `render.yaml`
6. Adicione variáveis de ambiente:
   ```
   NOME_ADVOGADO=EDSON MARCOS FERREIRA PRATTI JUNIOR
   MEISTERTASK_API_TOKEN=seu_token
   MEISTERTASK_SECTION_ID=seu_section_id
   ```
7. Deploy!

**Vantagens:**
- ✅ Gratuito
- ✅ SSL automático
- ✅ Build automático do GitHub
- ✅ Suporta Streamlit perfeitamente

---

### Opção 3: Heroku (PAGO após trial)

#### Criar arquivo `Procfile`:
```
web: streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0
```

#### Deploy:
```bash
heroku login
heroku create nome-do-app
git push heroku main
```

---

### Opção 4: Railway.app (GRATUITO)

#### Passos:
1. Acesse https://railway.app
2. New Project → Deploy from GitHub
3. Selecione o repositório
4. Adicione variáveis de ambiente
5. Railway detecta Streamlit automaticamente

---

## 🚫 Por que NÃO usar Vercel?

| Aspecto | Vercel | Streamlit Cloud/Render |
|---------|--------|------------------------|
| Suporte Streamlit | ❌ Não nativo | ✅ Nativo |
| WebSocket | ❌ Limitado | ✅ Total |
| Timeout | ❌ 10s (free) | ✅ Ilimitado |
| Persistência | ❌ Serverless | ✅ Servidor contínuo |
| Custo | 💰 Pago para funcionar | ✅ Gratuito |

---

## 🛠️ Se REALMENTE quiser usar Vercel (NÃO RECOMENDADO)

### Limitações:
- App pode ficar lento ou não funcionar
- Timeout em operações longas
- Perda de estado da sessão
- Custos adicionais

### Configuração:

1. **Arquivo vercel.json** (já criado):
```json
{
  "version": 2,
  "builds": [
    {
      "src": "dashboard.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "dashboard.py"
    }
  ]
}
```

2. **Adicionar no requirements.txt**:
```
streamlit==1.31.0
```

3. **Variáveis de ambiente no Vercel**:
   - Settings → Environment Variables
   - Adicionar cada variável do `.env`

4. **Deploy**:
```bash
vercel --prod
```

### Problemas esperados:
- ⚠️ Conexões WebSocket podem falhar
- ⚠️ Session state pode não persistir
- ⚠️ Funcionalidades interativas limitadas
- ⚠️ Timeouts frequentes

---

## 📊 Comparação de Plataformas

| Plataforma | Custo | Facilidade | Compatibilidade | Recomendação |
|------------|-------|------------|-----------------|--------------|
| **Streamlit Cloud** | Gratuito | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🏆 MELHOR |
| **Render** | Gratuito | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Ótima |
| **Railway** | Gratuito | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Boa |
| **Heroku** | Pago | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Ok |
| **Vercel** | Pago | ⭐⭐ | ⭐ | ❌ Evitar |

---

## 🎯 Recomendação Final

### Use **Streamlit Cloud** ou **Render**

**Streamlit Cloud:**
- Mais fácil
- Feito para Streamlit
- Gratuito
- Deploy em 2 minutos

**Render:**
- Configuração já pronta (`render.yaml`)
- Gratuito
- Confiável
- SSL incluso

---

## 📞 Suporte

Se escolher Streamlit Cloud ou Render e tiver problemas, posso ajudar com:
- Configuração de variáveis de ambiente
- Debug de erros de deploy
- Otimização de performance
- Configuração de domínio customizado

---

**Última atualização:** 3 de fevereiro de 2026  
**Status:** ⚠️ Vercel não recomendado para Streamlit
