#!/bin/bash
# Este script vai corrigir o dashboard.py adicionando o gerenciamento de duplicatas

echo "🔧 Corrigindo dashboard.py..."

# Backup
cp dashboard.py dashboard.py.bkp

# Baixa a versão correta do repositório remoto
curl -s -o dashboard_temp.py 'https://raw.githubusercontent.com/edsonpratti/gmail-meistertask-automation/3e4a714/dashboard.py'

if [ -f dashboard_temp.py ]; then
    # Verifica se o arquivo baixado é válido
    if python3 -m py_compile dashboard_temp.py 2>/dev/null; then
        mv dashboard_temp.py dashboard.py
        echo "✅ dashboard.py atualizado com sucesso!"
        wc -l dashboard.py
    else
        echo "❌ Arquivo baixado tem erros de sintaxe"
        rm dashboard_temp.py
    fi
else
    echo "❌ Falha ao baixar arquivo"
fi
