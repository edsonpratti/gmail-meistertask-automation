#!/bin/bash
cd ~/Documents/gmail-meistertask-automation
pkill -9 streamlit 2>/dev/null
pkill -9 -f dashboard.py 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null
sleep 3
streamlit run dashboard.py --server.port=8501 > /dev/null 2>&1 &
sleep 6
if curl -s http://localhost:8501 > /dev/null; then
  open http://localhost:8501
  echo "✅ Sistema rodando em http://localhost:8501"
else
  echo "❌ Erro ao iniciar. Verifique se a porta 8501 está livre"
fi
