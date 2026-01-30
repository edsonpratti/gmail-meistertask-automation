#!/bin/bash
# Script de inicialização do sistema Gmail → MeisterTask
# Uso: ./start.sh

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Iniciando Sistema Gmail → MeisterTask${NC}\n"

# Vai para o diretório correto
cd "$(dirname "$0")"

# 1. Para qualquer instância do Streamlit rodando
echo -e "${YELLOW}🛑 Parando instâncias anteriores...${NC}"
pkill -9 streamlit 2>/dev/null
pkill -9 -f "dashboard.py" 2>/dev/null
sleep 2

# 2. Verifica se a porta 8501 está livre
PORT_CHECK=$(lsof -ti:8501)
if [ ! -z "$PORT_CHECK" ]; then
    echo -e "${RED}⚠️  Porta 8501 ocupada. Liberando...${NC}"
    kill -9 $PORT_CHECK 2>/dev/null
    sleep 1
fi

# 3. Verifica dependências
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}❌ Streamlit não encontrado!${NC}"
    echo -e "${YELLOW}Instalando...${NC}"
    pip3 install streamlit
fi

# 4. Inicia o Streamlit
echo -e "${GREEN}✅ Iniciando dashboard...${NC}\n"

# Limpa cache do Streamlit
rm -rf ~/.streamlit/cache 2>/dev/null

# Inicia em background com output em log
nohup streamlit run dashboard.py \
    --server.port=8501 \
    --server.address=localhost \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    > streamlit.log 2>&1 &

STREAMLIT_PID=$!

# 5. Aguarda inicialização
echo -e "${YELLOW}⏳ Aguardando inicialização...${NC}"
sleep 5

# 6. Verifica se está rodando
if ps -p $STREAMLIT_PID > /dev/null; then
    # Testa conexão HTTP
    if curl -s http://localhost:8501 > /dev/null; then
        echo -e "\n${GREEN}✅ Sistema iniciado com sucesso!${NC}\n"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "${GREEN}📍 Acesse o sistema em:${NC}"
        echo -e ""
        echo -e "   ${YELLOW}http://localhost:8501${NC}"
        echo -e ""
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e ""
        echo -e "💡 Dica: Adicione um bookmark no seu navegador!"
        echo -e ""
        echo -e "🔄 Para reiniciar: ./start.sh"
        echo -e "🛑 Para parar: ./stop.sh"
        echo -e "📋 Ver logs: tail -f streamlit.log"
        echo -e ""
        
        # Abre automaticamente no navegador padrão
        if command -v open &> /dev/null; then
            sleep 2
            open http://localhost:8501
        fi
    else
        echo -e "${RED}❌ Erro: Sistema não está respondendo${NC}"
        echo -e "📋 Verifique os logs: tail -f streamlit.log"
        exit 1
    fi
else
    echo -e "${RED}❌ Erro ao iniciar o sistema${NC}"
    echo -e "📋 Verifique os logs: tail -f streamlit.log"
    exit 1
fi
