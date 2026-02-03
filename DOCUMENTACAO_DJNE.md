# 📚 Documentação Completa: Busca de Publicações no DJNE

**Data:** 2 de fevereiro de 2026  
**Versão:** 1.0  
**Sistema:** Automação DJNE → MeisterTask

---

## 🎯 Visão Geral

O sistema automatiza a busca de publicações judiciais no **Diário de Justiça Eletrônico Nacional (DJNE)** através de web scraping e acesso à API do CNJ, extraindo intimações e publicações para advogados específicos.

---

## 🔧 Arquitetura da Solução

### Componentes Principais
- **djne_scraper.py**: Módulo principal de scraping
- **dashboard.py**: Interface Streamlit que utiliza o scraper
- **test_djne.py**: Testes automatizados

---

## 📋 Função Principal: `buscar_publicacoes_djne()`

**Localização:** `djne_scraper.py` (linhas 12-213)

### Parâmetros
```python
buscar_publicacoes_djne(nome_advogado, data_inicio, data_fim=None)
```

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `nome_advogado` | `str` | Nome completo do advogado em MAIÚSCULAS |
| `data_inicio` | `date` ou `str` | Data inicial da busca (YYYY-MM-DD) |
| `data_fim` | `date` ou `str` | Data final (opcional, default = data_inicio) |

### Retorno
```python
[
    {
        'process_number': '1234567-12.2024.1.23.4567',
        'orgao': 'Tribunal Regional Federal da 1ª Região',
        'data_disponibilizacao': '22/01/2026',
        'tipo_comunicacao': 'Intimação',
        'content': 'Texto completo da publicação...',
        'source_subject': 'DJNE - 1234567-12.2024.1.23.4567',
        'origem': 'DJNE'
    },
    ...
]
```

---

## 🔄 Fluxo de Execução Completo

### Etapa 1: Preparação dos Dados
```python
# Converte datas para string no formato YYYY-MM-DD
if isinstance(data_inicio, date):
    data_inicio_str = data_inicio.strftime('%Y-%m-%d')
else:
    data_inicio_str = data_inicio

# Se data_fim não fornecida, usa data_inicio
if data_fim is None:
    data_fim_str = data_inicio_str
elif isinstance(data_fim, date):
    data_fim_str = data_fim.strftime('%Y-%m-%d')
else:
    data_fim_str = data_fim
```

**Exemplo:**
- Input: `date(2026, 2, 2)`
- Output: `"2026-02-02"`

---

### Etapa 2: Construção da URL

```python
# URL de consulta do DJNE
base_url = "https://comunica.pje.jus.br/consulta"

# Monta URL com parâmetros
url = f"{base_url}?texto={nome_advogado.replace(' ', '%20')}&dataDisponibilizacaoInicio={data_inicio_str}&dataDisponibilizacaoFim={data_fim_str}"
```

**Exemplo de URL Gerada:**
```
https://comunica.pje.jus.br/consulta?texto=EDSON%20MARCOS%20FERREIRA%20PRATTI%20JUNIOR&dataDisponibilizacaoInicio=2026-02-02&dataDisponibilizacaoFim=2026-02-02
```

**Componentes:**
- `texto`: Nome do advogado (espaços convertidos para %20)
- `dataDisponibilizacaoInicio`: Data inicial (YYYY-MM-DD)
- `dataDisponibilizacaoFim`: Data final (YYYY-MM-DD)

---

### Etapa 3: Configuração de Headers

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
```

**Motivo:** Simula um browser real para evitar bloqueio por sistemas anti-bot

**Detalhes:**
- `User-Agent`: Identifica como Chrome 120 no macOS
- `Accept`: Define tipos de conteúdo aceitos
- `Accept-Language`: Prioriza português brasileiro
- `Accept-Encoding`: Permite compressão gzip/br
- `Connection`: Mantém conexão ativa
- `Upgrade-Insecure-Requests`: Indica suporte a HTTPS

---

### Etapa 4: Requisição à Página Principal

```python
# Cria uma sessão para manter cookies
session = requests.Session()

# Primeira requisição - carrega a página
print(f"DEBUG: Acessando URL: {url}")
response = session.get(url, headers=headers, timeout=30)
response.raise_for_status()
print(f"DEBUG: Resposta HTTP: {response.status_code}")
```

**O que acontece:**
1. Cria sessão HTTP (mantém cookies entre requisições)
2. Faz GET na URL principal
3. Timeout de 30 segundos
4. Verifica status HTTP (lança exceção se erro 4xx/5xx)
5. Loga o status code

**Status esperado:** 200 OK

---

### Etapa 5: Tentativa de Acesso à API (Método Preferencial)

```python
# URL da API baseada na análise do site
api_url = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

params = {
    'texto': nome_advogado,
    'dataDisponibilizacaoInicio': data_inicio_str,
    'dataDisponibilizacaoFim': data_fim_str,
    'tamanho': 100,  # máximo de resultados
    'pagina': 0      # primeira página
}

print(f"DEBUG: Chamando API: {api_url}")
print(f"DEBUG: Parâmetros: {params}")
api_response = session.get(api_url, params=params, headers=headers, timeout=30)
print(f"DEBUG: API Response Status: {api_response.status_code}")
```

**Endpoint da API:**
```
GET https://comunicaapi.pje.jus.br/api/v1/comunicacao
```

**Query Parameters:**
- `texto`: Nome do advogado (sem encoding)
- `dataDisponibilizacaoInicio`: Data inicial
- `dataDisponibilizacaoFim`: Data final
- `tamanho`: Limite de resultados (máx 100)
- `pagina`: Número da página (zero-indexed)

#### Estrutura da Resposta da API

**Formato esperado:**
```json
{
    "items": [
        {
            "numeroprocessocommascara": "1234567-12.2024.1.23.4567",
            "nomeOrgao": "Tribunal Regional Federal da 1ª Região",
            "datadisponibilizacao": "2026-02-02T00:00:00",
            "tipoComunicacao": "Intimação",
            "texto": "Conteúdo da publicação..."
        }
    ],
    "total": 5,
    "page": 0,
    "size": 100
}
```

**Variações possíveis:**
- Campos de itens: `items`, `content`, ou `data`
- Campo de processo: `numeroprocessocommascara`, `numero_processo`, `numeroProcesso`
- Campo de órgão: `nomeOrgao`, `orgao`
- Campo de data: `datadisponibilizacao`, `data_disponibilizacao`, `dataDisponibilizacao`
- Campo de tipo: `tipoComunicacao`, `tipo_comunicacao`
- Campo de conteúdo: `texto`, `conteudo`, `content`

---

### Etapa 6: Processamento da Resposta JSON

```python
if api_response.status_code == 200:
    try:
        data = api_response.json()
        print(f"DEBUG: JSON recebido, tipo: {type(data)}")
        
        # A API retorna JSON com lista de comunicações
        if isinstance(data, dict):
            # Tenta múltiplos nomes de campos
            comunicacoes = data.get('items', []) or data.get('content', []) or data.get('data', [])
            total = data.get('total', len(comunicacoes))
            print(f"DEBUG: Encontradas {len(comunicacoes)} comunicações (total: {total})")
        else:
            comunicacoes = []
            print(f"DEBUG: Resposta não é dict, é {type(data)}")
        
        # Processa cada comunicação
        for com in comunicacoes:
            # Extrai número do processo (múltiplos formatos)
            numero_processo = (
                com.get('numeroprocessocommascara') or
                com.get('numero_processo') or
                com.get('numeroProcesso') or
                'Não identificado'
            )
            
            publicacao = {
                'process_number': numero_processo,
                'orgao': com.get('nomeOrgao') or com.get('orgao') or 'Não identificado',
                'data_disponibilizacao': (
                    com.get('datadisponibilizacao') or
                    com.get('data_disponibilizacao') or
                    com.get('dataDisponibilizacao') or ''
                ),
                'tipo_comunicacao': (
                    com.get('tipoComunicacao') or
                    com.get('tipo_comunicacao') or
                    'Intimação'
                ),
                'content': (
                    com.get('texto') or
                    com.get('conteudo') or
                    com.get('content') or ''
                ),
                'source_subject': f"DJNE - {numero_processo}",
                'origem': 'DJNE'
            }
            
            print(f"DEBUG: Publicação extraída - Processo: {numero_processo}")
            publicacoes.append(publicacao)
        
        print(f"DEBUG: Total de publicações extraídas da API: {len(publicacoes)}")
        return publicacoes
        
    except json.JSONDecodeError as e:
        # API não retornou JSON, tenta fazer scraping do HTML
        print(f"DEBUG: Erro ao decodificar JSON: {e}")
        print(f"DEBUG: Conteúdo da resposta (primeiros 500 chars): {api_response.text[:500]}")
        pass
```

**Estratégia de Fallback:**
- Se status ≠ 200 → vai para scraping HTML
- Se JSON inválido → vai para scraping HTML
- Se JSON vazio → retorna lista vazia
- Se sucesso → retorna lista de publicações

---

### Etapa 7: Fallback - Scraping HTML

Quando a API falha ou não retorna JSON válido:

```python
# Fallback: scraping do HTML se API não funcionou
print("DEBUG: Usando fallback de scraping HTML...")
from bs4 import BeautifulSoup

soup = BeautifulSoup(response.text, 'html.parser')
texto_completo = soup.get_text(separator='\n')
print(f"DEBUG: HTML convertido para texto, tamanho: {len(texto_completo)} caracteres")
```

#### Padrão de Busca de Processos

```python
# Procura pelo padrão "Processo XXXX"
processo_pattern = r'Processo\s+(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'

# Encontra todos os processos
matches = list(re.finditer(processo_pattern, texto_completo, re.IGNORECASE))
print(f"DEBUG: Encontrados {len(matches)} processos no HTML")
```

**Regex explicado:**
- `Processo\s+`: Palavra "Processo" + espaços
- `\d{7}`: 7 dígitos (número sequencial)
- `-\d{2}`: Hífen + 2 dígitos (ano de ajuizamento)
- `\.\d{4}`: Ponto + 4 dígitos (ano completo)
- `\.\d+`: Ponto + 1 ou mais dígitos (segmento)
- `\.\d{2}`: Ponto + 2 dígitos (tribunal)
- `\.\d{4}`: Ponto + 4 dígitos (unidade)

**Exemplo:** `Processo 1234567-12.2024.1.23.4567`

#### Extração de Blocos de Conteúdo

```python
for i, match in enumerate(matches):
    numero_processo = match.group(1)
    
    # Início do conteúdo (logo após o número do processo)
    inicio = match.end()
    
    # Fim do conteúdo (início do próximo processo ou fim do texto)
    if i + 1 < len(matches):
        fim = matches[i + 1].start()
    else:
        fim = len(texto_completo)
    
    # Extrai o bloco de conteúdo desta publicação
    bloco_conteudo = texto_completo[inicio:fim].strip()
```

**Lógica:**
1. Para cada processo encontrado
2. Início = posição logo após o número
3. Fim = início do próximo processo (ou fim do documento)
4. Extrai substring entre início e fim
5. Remove espaços em branco nas bordas

#### Extração de Metadados

```python
# Extrai informações específicas usando regex
orgao_match = re.search(r'Órgão:\s*([^\n]+)', bloco_conteudo)
data_match = re.search(r'Data de disponibilização:\s*(\d{2}/\d{2}/\d{4})', bloco_conteudo)
tipo_match = re.search(r'Tipo de comunicação:\s*([^\n]+)', bloco_conteudo)

# Monta a publicação
publicacao = {
    'process_number': numero_processo,
    'orgao': orgao_match.group(1).strip() if orgao_match else 'Não identificado',
    'data_disponibilizacao': data_match.group(1) if data_match else '',
    'tipo_comunicacao': tipo_match.group(1).strip() if tipo_match else 'Intimação',
    'content': bloco_conteudo[:5000],  # Limita a 5000 caracteres
    'source_subject': f"DJNE - {numero_processo}",
    'origem': 'DJNE'
}

publicacoes.append(publicacao)
```

**Padrões de Extração:**

| Campo | Regex | Exemplo |
|-------|-------|---------|
| Órgão | `r'Órgão:\s*([^\n]+)'` | `Órgão: TRF1` |
| Data | `r'Data de disponibilização:\s*(\d{2}/\d{2}/\d{4})'` | `Data de disponibilização: 02/02/2026` |
| Tipo | `r'Tipo de comunicação:\s*([^\n]+)'` | `Tipo de comunicação: Intimação` |

**Limitações:**
- Conteúdo limitado a 5000 caracteres
- Se campo não encontrado, usa valor padrão

---

## 🛡️ Tratamento de Erros

### Sistema de Logging Detalhado

```python
print(f"DEBUG: Acessando URL: {url}")
print(f"DEBUG: Resposta HTTP: {response.status_code}")
print(f"DEBUG: Chamando API: {api_url}")
print(f"DEBUG: Parâmetros: {params}")
print(f"DEBUG: API Response Status: {api_response.status_code}")
print(f"DEBUG: JSON recebido, tipo: {type(data)}")
print(f"DEBUG: Encontradas {len(comunicacoes)} comunicações")
print(f"DEBUG: Publicação extraída - Processo: {numero_processo}")
print(f"DEBUG: Total de publicações extraídas da API: {len(publicacoes)}")
print(f"DEBUG: HTML convertido para texto, tamanho: {len(texto_completo)} caracteres")
print(f"DEBUG: Encontrados {len(matches)} processos no HTML")
```

**Vantagens:**
- Rastreamento completo do fluxo
- Identificação rápida de falhas
- Dados para debugging
- Visibilidade no console

### Captura de Exceções

```python
try:
    # Cria uma sessão para manter cookies
    session = requests.Session()
    
    # Requisições e processamento...
    
except json.JSONDecodeError as e:
    # API não retornou JSON válido
    print(f"DEBUG: Erro ao decodificar JSON: {e}")
    print(f"DEBUG: Conteúdo da resposta (primeiros 500 chars): {api_response.text[:500]}")
    # Tenta fallback HTML
    pass

except Exception as e:
    # Qualquer outro erro
    print(f"DEBUG: Exceção capturada: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    raise Exception(f"Erro ao processar publicações do DJNE: {str(e)}")
```

**Tipos de Exceções Tratadas:**

| Exceção | Causa | Ação |
|---------|-------|------|
| `json.JSONDecodeError` | Resposta não é JSON | Tenta scraping HTML |
| `requests.exceptions.Timeout` | Timeout (>30s) | Lança exceção com mensagem |
| `requests.exceptions.ConnectionError` | Sem conexão/DNS | Lança exceção com mensagem |
| `requests.exceptions.HTTPError` | Status 4xx/5xx | Lança exceção com mensagem |
| `Exception` (genérica) | Qualquer outro erro | Loga traceback completo |

---

## 🔧 Função Auxiliar: `contar_publicacoes_djne()`

**Localização:** `djne_scraper.py` (linhas 216-229)

### Assinatura
```python
def contar_publicacoes_djne(nome_advogado, data_inicio, data_fim=None):
    """
    Conta quantas publicações existem no DJNE sem fazer parsing completo
    
    Args:
        nome_advogado (str): Nome completo do advogado
        data_inicio (date ou str): Data inicial
        data_fim (date ou str, opcional): Data final
    
    Returns:
        int: Número de publicações encontradas
    """
```

### Implementação
```python
try:
    publicacoes = buscar_publicacoes_djne(nome_advogado, data_inicio, data_fim)
    return len(publicacoes)
except:
    return 0
```

### Uso
```python
# Verifica se há publicações antes de processar
total = contar_publicacoes_djne("JOÃO DA SILVA", date.today())

if total > 0:
    print(f"Existem {total} publicações para processar")
    # Busca e processa...
else:
    print("Nenhuma publicação encontrada")
```

**Vantagem:** Retorna 0 em caso de qualquer erro (silencioso)

---

## 📊 Padrões de Regex Utilizados

### 1. Número de Processo Judicial

```python
processo_pattern = r'(\d{7}-\d{2}\.\d{4}\.\d+\.\d{2}\.\d{4})'
```

**Estrutura do Número:**
```
1234567-12.2024.1.23.4567
│      │  │    │ │  │
│      │  │    │ │  └─ OOOO (unidade de origem)
│      │  │    │ └──── TT (tribunal)
│      │  │    └────── S (segmento da Justiça)
│      │  └─────────── AAAA (ano com 4 dígitos)
│      └────────────── DD (ano de ajuizamento)
└───────────────────── NNNNNNN (número sequencial)
```

**Componentes do Regex:**
- `\d{7}`: 7 dígitos (número sequencial único)
- `-`: Hífen separador
- `\d{2}`: 2 dígitos (ano de ajuizamento - últimos 2 dígitos)
- `\.`: Ponto separador (escapado)
- `\d{4}`: 4 dígitos (ano completo)
- `\.`: Ponto separador
- `\d+`: 1 ou mais dígitos (segmento: 1-9)
- `\.`: Ponto separador
- `\d{2}`: 2 dígitos (código do tribunal)
- `\.`: Ponto separador
- `\d{4}`: 4 dígitos (unidade de origem)

**Exemplos válidos:**
- `1234567-12.2024.1.23.4567`
- `0001234-56.2023.5.09.0001`
- `9876543-21.2026.8.26.0100`

### 2. Órgão Judicial

```python
orgao_pattern = r'Órgão:\s*([^\n]+)'
```

**Componentes:**
- `Órgão:`: Texto literal
- `\s*`: Zero ou mais espaços em branco
- `([^\n]+)`: Captura tudo até quebra de linha

**Exemplos:**
```
Input: "Órgão: Tribunal Regional Federal da 1ª Região"
Match: "Tribunal Regional Federal da 1ª Região"

Input: "Órgão:TRF1"
Match: "TRF1"

Input: "Órgão:    TJSP - 5ª Câmara de Direito Público"
Match: "TJSP - 5ª Câmara de Direito Público"
```

### 3. Data de Disponibilização

```python
data_pattern = r'Data de disponibilização:\s*(\d{2}/\d{2}/\d{4})'
```

**Componentes:**
- `Data de disponibilização:`: Texto literal
- `\s*`: Zero ou mais espaços
- `(\d{2}/\d{2}/\d{4})`: Captura data DD/MM/AAAA

**Exemplos:**
```
Input: "Data de disponibilização: 02/02/2026"
Match: "02/02/2026"

Input: "Data de disponibilização:22/01/2026"
Match: "22/01/2026"
```

### 4. Tipo de Comunicação

```python
tipo_pattern = r'Tipo de comunicação:\s*([^\n]+)'
```

**Tipos comuns:**
- Intimação
- Citação
- Decisão
- Sentença
- Acórdão
- Despacho

**Exemplos:**
```
Input: "Tipo de comunicação: Intimação"
Match: "Intimação"

Input: "Tipo de comunicação: Decisão Monocrática"
Match: "Decisão Monocrática"
```

---

## 🧪 Testes Automatizados

### Script de Teste: test_djne.py

**Arquivo completo de teste:**

```python
#!/usr/bin/env python3
"""
Teste do DJNE Scraper
"""
import sys
from datetime import date

print("=" * 60)
print("TESTE DO DJNE SCRAPER")
print("=" * 60)

# Teste de importação
print("\n1. Testando importação...")
try:
    from djne_scraper import buscar_publicacoes_djne
    print("✅ Importação OK")
except Exception as e:
    print(f"❌ Erro na importação: {e}")
    sys.exit(1)

# Teste de dependências
print("\n2. Testando dependências...")
try:
    import requests
    import re
    from bs4 import BeautifulSoup
    print("✅ Dependências OK (requests, re, BeautifulSoup)")
except Exception as e:
    print(f"❌ Erro nas dependências: {e}")
    print("Execute: pip install requests beautifulsoup4")
    sys.exit(1)

# Teste da função
print("\n3. Testando função buscar_publicacoes_djne...")
nome = "EDSON MARCOS FERREIRA PRATTI JUNIOR"
data_teste = date.today()

print(f"   Nome: {nome}")
print(f"   Data: {data_teste}")

try:
    publicacoes = buscar_publicacoes_djne(nome, data_teste)
    print(f"\n✅ Função executada com sucesso!")
    print(f"   Total de publicações: {len(publicacoes)}")
    
    if publicacoes:
        print("\n4. Detalhes da primeira publicação:")
        pub = publicacoes[0]
        print(f"   - Processo: {pub.get('process_number', 'N/A')}")
        print(f"   - Órgão: {pub.get('orgao', 'N/A')}")
        print(f"   - Data: {pub.get('data_disponibilizacao', 'N/A')}")
        print(f"   - Tipo: {pub.get('tipo_comunicacao', 'N/A')}")
        print(f"   - Origem: {pub.get('origem', 'N/A')}")
        
        conteudo = pub.get('content', '')
        print(f"   - Tamanho do conteúdo: {len(conteudo)} caracteres")
        print(f"   - Preview: {conteudo[:200]}...")
    else:
        print("\n⚠️ Nenhuma publicação encontrada para a data de hoje")
        print("   Isso pode ser normal se não houver publicações novas")
        
except Exception as e:
    print(f"\n❌ Erro ao executar função: {type(e).__name__}")
    print(f"   Mensagem: {str(e)}")
    import traceback
    print("\n   Traceback completo:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)
```

### Como Executar

```bash
# Executar teste
python3 test_djne.py

# Ou testar diretamente o scraper
python3 djne_scraper.py
```

### Saída Esperada (Sucesso)

```
============================================================
TESTE DO DJNE SCRAPER
============================================================

1. Testando importação...
✅ Importação OK

2. Testando dependências...
✅ Dependências OK (requests, re, BeautifulSoup)

3. Testando função buscar_publicacoes_djne...
   Nome: EDSON MARCOS FERREIRA PRATTI JUNIOR
   Data: 2026-02-02

DEBUG: Acessando URL: https://comunica.pje.jus.br/consulta?texto=...
DEBUG: Resposta HTTP: 200
DEBUG: Chamando API: https://comunicaapi.pje.jus.br/api/v1/comunicacao
DEBUG: Parâmetros: {'texto': '...', 'dataDisponibilizacaoInicio': '2026-02-02', ...}
DEBUG: API Response Status: 200
DEBUG: JSON recebido, tipo: <class 'dict'>
DEBUG: Encontradas 5 comunicações (total: 5)
DEBUG: Publicação extraída - Processo: 1234567-12.2024.1.23.4567
DEBUG: Publicação extraída - Processo: 2345678-23.2024.1.23.5678
DEBUG: Total de publicações extraídas da API: 5

✅ Função executada com sucesso!
   Total de publicações: 5

4. Detalhes da primeira publicação:
   - Processo: 1234567-12.2024.1.23.4567
   - Órgão: Tribunal Regional Federal da 1ª Região
   - Data: 02/02/2026
   - Tipo: Intimação
   - Origem: DJNE
   - Tamanho do conteúdo: 1234 caracteres
   - Preview: INTIMAÇÃO - Processo: 1234567-12.2024.1.23.4567...

============================================================
TESTE CONCLUÍDO
============================================================
```

### Saída Esperada (Sem Publicações)

```
✅ Função executada com sucesso!
   Total de publicações: 0

⚠️ Nenhuma publicação encontrada para a data de hoje
   Isso pode ser normal se não houver publicações novas
```

### Checklist de Testes

- [ ] Importação do módulo funciona
- [ ] Dependências instaladas (requests, beautifulsoup4)
- [ ] Conexão com DJNE estabelecida (status 200)
- [ ] API retorna resposta (JSON ou HTML)
- [ ] Publicações extraídas corretamente
- [ ] Campos obrigatórios presentes (process_number, content, origem)
- [ ] Sem erros de traceback

---

## 🚀 Integração com Dashboard

### Fluxo no dashboard.py

```python
# Quando usuário seleciona "DJNE" como fonte de dados
if data_source == 'djne':
    # Obtém nome do advogado das variáveis de ambiente
    nome_advogado = os.getenv('NOME_ADVOGADO', 'EDSON MARCOS FERREIRA PRATTI JUNIOR')
    
    # Mostra spinner de carregamento
    with st.spinner('🔍 Buscando publicações no DJNE...'):
        # Chama função de scraping
        publicacoes = buscar_publicacoes_djne(
            nome_advogado=nome_advogado,
            data_inicio=date_from,
            data_fim=date_to
        )
    
    # Processa resultado
    if publicacoes:
        # Salva no session state
        st.session_state.extracted_publications = publicacoes
        # Pula para etapa 3 (validação)
        st.session_state.current_step = 3
        # Mostra mensagem de sucesso
        st.success(f'✅ {len(publicacoes)} publicações encontradas!')
        st.rerun()
    else:
        # Nenhuma publicação encontrada
        st.warning('⚠️ Nenhuma publicação encontrada para o período selecionado')
```

### Diferença entre Gmail e DJNE

| Aspecto | Gmail | DJNE |
|---------|-------|------|
| **Etapas** | 1 → 2 → 3 → 4 | 1 → 3 → 4 |
| **Seleção de emails** | Sim (Etapa 2) | Não (pula direto) |
| **Extração** | De emails selecionados | Direta da API/site |
| **Fonte** | API do Gmail | API CNJ / Web scraping |
| **Autenticação** | OAuth2 (token.pickle) | Nenhuma |

### Session State

```python
# Estado após busca DJNE bem-sucedida
st.session_state = {
    'current_step': 3,                    # Pula para validação
    'data_source': 'djne',                # Fonte selecionada
    'extracted_publications': [           # Publicações encontradas
        {
            'process_number': '...',
            'content': '...',
            'orgao': '...',
            'data_disponibilizacao': '...',
            'tipo_comunicacao': '...',
            'source_subject': '...',
            'origem': 'DJNE'
        },
        ...
    ],
    'filters': {                          # Filtros aplicados
        'date_from': date(2026, 2, 2),
        'date_to': date(2026, 2, 2)
    }
}
```

---

## ⚙️ Configuração Necessária

### 1. Variáveis de Ambiente (.env)

```bash
# Nome completo do advogado (MAIÚSCULAS)
NOME_ADVOGADO="EDSON MARCOS FERREIRA PRATTI JUNIOR"

# Configurações do MeisterTask (para criação de tarefas)
MEISTERTASK_API_TOKEN=seu_token_aqui
MEISTERTASK_SECTION_ID=id_da_secao
```

### 2. Dependências (requirements.txt)

```txt
# Web scraping
requests>=2.31.0
beautifulsoup4>=4.12.0

# Dashboard (opcional)
streamlit>=1.28.0

# Processamento de texto (opcional - para Gmail)
html2text>=2020.1.16
```

### 3. Instalação

```bash
# Instalar todas as dependências
pip install -r requirements.txt

# Ou apenas as essenciais para DJNE
pip install requests beautifulsoup4
```

### 4. Estrutura de Diretórios

```
projeto/
├── djne_scraper.py          # Módulo principal
├── dashboard.py             # Interface Streamlit
├── test_djne.py             # Testes
├── requirements.txt         # Dependências
├── .env                     # Variáveis de ambiente
├── DOCUMENTACAO_DJNE.md     # Esta documentação
└── README.md                # Documentação geral
```

---

## 🔍 Casos de Uso

### Caso 1: Busca de um dia específico

```python
from djne_scraper import buscar_publicacoes_djne
from datetime import date

# Busca publicações de hoje
publicacoes = buscar_publicacoes_djne(
    nome_advogado="JOÃO DA SILVA",
    data_inicio=date.today()
)

print(f"Encontradas {len(publicacoes)} publicações")
```

### Caso 2: Busca de período (múltiplos dias)

```python
from datetime import date, timedelta

# Busca últimos 7 dias
data_fim = date.today()
data_inicio = data_fim - timedelta(days=7)

publicacoes = buscar_publicacoes_djne(
    nome_advogado="MARIA SANTOS OLIVEIRA",
    data_inicio=data_inicio,
    data_fim=data_fim
)

print(f"Período: {data_inicio} a {data_fim}")
print(f"Total: {len(publicacoes)} publicações")
```

### Caso 3: Apenas verificar se há publicações

```python
from djne_scraper import contar_publicacoes_djne
from datetime import date

# Conta sem processar
total = contar_publicacoes_djne(
    nome_advogado="JOSÉ OLIVEIRA",
    data_inicio=date.today()
)

if total > 0:
    print(f"⚠️ Você tem {total} publicações novas!")
else:
    print("✅ Nenhuma publicação nova")
```

### Caso 4: Processar e salvar em arquivo

```python
import json

publicacoes = buscar_publicacoes_djne(
    nome_advogado="PEDRO SANTOS",
    data_inicio=date(2026, 2, 1),
    data_fim=date(2026, 2, 2)
)

# Salva em JSON
with open('publicacoes.json', 'w', encoding='utf-8') as f:
    json.dump(publicacoes, f, ensure_ascii=False, indent=2)

print(f"Salvas {len(publicacoes)} publicações em publicacoes.json")
```

### Caso 5: Filtrar por tipo de comunicação

```python
publicacoes = buscar_publicacoes_djne(
    nome_advogado="ANA PAULA SILVA",
    data_inicio=date.today()
)

# Filtra apenas intimações
intimacoes = [
    pub for pub in publicacoes 
    if pub['tipo_comunicacao'].lower() == 'intimação'
]

print(f"Total: {len(publicacoes)}")
print(f"Intimações: {len(intimacoes)}")
```

### Caso 6: Agrupar por órgão

```python
from collections import defaultdict

publicacoes = buscar_publicacoes_djne(
    nome_advogado="CARLOS EDUARDO",
    data_inicio=date.today()
)

# Agrupa por órgão
por_orgao = defaultdict(list)
for pub in publicacoes:
    orgao = pub['orgao']
    por_orgao[orgao].append(pub)

# Exibe estatísticas
for orgao, pubs in por_orgao.items():
    print(f"{orgao}: {len(pubs)} publicações")
```

---

## ⚠️ Limitações e Considerações

### Limitações Técnicas

| Aspecto | Limitação | Impacto |
|---------|-----------|---------|
| **Timeout** | 30 segundos | Pode falhar em conexões lentas |
| **Tamanho do conteúdo** | 5000 caracteres (HTML) | Ilimitado na API |
| **Rate limiting** | Não implementado | Risco de bloqueio |
| **Resultados por página** | 100 (API) | Múltiplas requisições necessárias |
| **Paginação** | Apenas página 0 | Não busca páginas seguintes |

### Dependências Externas

**API do CNJ:**
- ✅ **Vantagem:** Retorna dados estruturados (JSON)
- ⚠️ **Risco:** Pode mudar sem aviso prévio
- ⚠️ **Risco:** Nomes de campos podem variar
- ⚠️ **Risco:** Pode ficar indisponível

**HTML do site:**
- ✅ **Vantagem:** Fallback quando API falha
- ⚠️ **Risco:** Estrutura pode mudar
- ⚠️ **Risco:** Mais lento que API
- ⚠️ **Risco:** Regex pode quebrar

### Dias sem Publicação

É **completamente normal** não encontrar publicações em:

- 🚫 **Sábados e domingos** (expediente forense não funciona)
- 🚫 **Feriados nacionais** (sem publicações)
- 🚫 **Feriados estaduais** (depende do tribunal)
- 🚫 **Recesso forense** (janeiro/julho - períodos específicos)
- ✅ **Dias sem intimações** para o advogado específico

### Situações de Erro Comum

**1. Nenhuma publicação encontrada**
```
Possíveis causas:
- Fim de semana / feriado
- Nome do advogado incorreto
- Sem publicações naquele dia
- API temporariamente fora do ar
```

**2. Timeout**
```
Possíveis causas:
- Conexão de internet lenta
- Site DJNE lento/sobrecarregado
- Firewall bloqueando acesso
```

**3. Erro de JSON**
```
Possíveis causas:
- API retornou HTML ao invés de JSON
- Mudança na estrutura da API
- Resposta de erro do servidor
```

---

## 🔄 Fluxo Completo de Dados

```
┌─────────────────────────────────────────────────────────────┐
│                        USUÁRIO                               │
│   Define: Nome do advogado, Data inicial, Data final        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DASHBOARD                               │
│   Chama: buscar_publicacoes_djne(nome, data_inicio, ...)   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DJNE_SCRAPER.PY                            │
│   1. Monta URL com parâmetros                                │
│   2. Configura headers (simula browser)                      │
│   3. Cria sessão HTTP                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               DJNE - Página Web Principal                    │
│   GET https://comunica.pje.jus.br/consulta?...             │
│   Retorna: HTML da página de busca                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DJNE_SCRAPER.PY                            │
│   Tenta acessar API JSON                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 DJNE - API JSON                              │
│   GET https://comunicaapi.pje.jus.br/api/v1/comunicacao    │
│   Retorna: JSON com lista de comunicações                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                ┌────────┴────────┐
                │                 │
            Sucesso?             Falha?
                │                 │
                ▼                 ▼
    ┌───────────────────┐  ┌──────────────────┐
    │ Processa JSON     │  │ Fallback: HTML   │
    │ - Extrai campos   │  │ - BeautifulSoup  │
    │ - Monta objetos   │  │ - Regex extract  │
    └────────┬──────────┘  └────────┬─────────┘
             │                      │
             └──────────┬───────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  Lista de Publicações         │
        │  [                             │
        │    {                           │
        │      process_number: "...",    │
        │      orgao: "...",             │
        │      content: "...",           │
        │      ...                       │
        │    }                           │
        │  ]                             │
        └────────────┬──────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │      DASHBOARD              │
        │  - Salva em session_state   │
        │  - Avança para Etapa 3      │
        │  - Exibe para validação     │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │       USUÁRIO               │
        │  - Valida publicações       │
        │  - Seleciona quais criar    │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │     MEISTERTASK             │
        │  - Cria tarefas             │
        │  - Retorna confirmação      │
        └────────────────────────────┘
```

---

## 📈 Estatísticas e Métricas

### Logs de Performance

```python
import time

inicio = time.time()
publicacoes = buscar_publicacoes_djne(nome, data_inicio)
fim = time.time()

print(f"Tempo de execução: {fim - inicio:.2f} segundos")
print(f"Publicações encontradas: {len(publicacoes)}")
print(f"Tempo médio por publicação: {(fim - inicio) / max(len(publicacoes), 1):.2f}s")
```

### Exemplo de Métricas

```
Tempo de execução: 2.45 segundos
Publicações encontradas: 5
Tempo médio por publicação: 0.49s

Detalhamento:
- Request página principal: 0.8s
- Request API JSON: 1.2s
- Processamento JSON: 0.3s
- Montagem de objetos: 0.15s
```

---

## 🛠️ Manutenção e Debugging

### Checklist de Troubleshooting

#### 1. Verificar Conectividade
```bash
# Testar acesso ao site
curl -I https://comunica.pje.jus.br/consulta

# Deve retornar: HTTP/2 200
```

#### 2. Testar API Diretamente
```bash
curl "https://comunicaapi.pje.jus.br/api/v1/comunicacao?texto=TESTE&dataDisponibilizacaoInicio=2026-02-02&dataDisponibilizacaoFim=2026-02-02&tamanho=10&pagina=0"
```

#### 3. Verificar Dependências
```bash
pip list | grep -E "requests|beautifulsoup4"
```

#### 4. Executar Teste
```bash
python3 test_djne.py
```

### Problemas Comuns e Soluções

| Problema | Causa Provável | Solução |
|----------|----------------|---------|
| `ModuleNotFoundError: requests` | Biblioteca não instalada | `pip install requests` |
| `ModuleNotFoundError: bs4` | BeautifulSoup não instalado | `pip install beautifulsoup4` |
| `Timeout after 30s` | Conexão lenta ou site fora | Verificar internet / tentar novamente |
| `JSON decode error` | API retornou HTML | Normal, usa fallback HTML |
| `0 publicações` | Sem publicações no dia | Normal em fins de semana/feriados |
| `Não identificado` em campos | Padrão regex não encontrou | Revisar estrutura do HTML/JSON |

---

## 📚 Referências

### URLs Importantes

- **Site de Consulta:** https://comunica.pje.jus.br/consulta
- **API de Comunicações:** https://comunicaapi.pje.jus.br/api/v1/comunicacao
- **Documentação PJe:** https://www.pje.jus.br/

### Bibliotecas Utilizadas

- **requests:** https://docs.python-requests.org/
- **BeautifulSoup:** https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **re (regex):** https://docs.python.org/3/library/re.html

### Padrões e Convenções

- **Número de Processo:** Resolução CNJ nº 65/2008
- **Data formato:** ISO 8601 (YYYY-MM-DD) para API, DD/MM/YYYY para exibição
- **Encoding:** UTF-8 para todos os arquivos

---

## 🔐 Segurança e Boas Práticas

### Headers Seguros
✅ Usa User-Agent realista  
✅ Aceita compressão (gzip, br)  
✅ Define Accept-Language apropriado  

### Proteção de Dados
✅ Não armazena credenciais no código  
✅ Usa variáveis de ambiente (.env)  
✅ Não loga dados sensíveis  

### Rate Limiting (Recomendado)
```python
import time

for nome in lista_advogados:
    publicacoes = buscar_publicacoes_djne(nome, date.today())
    # Aguarda 2 segundos entre requisições
    time.sleep(2)
```

### Tratamento de Erros
✅ Try/catch em todas as operações de rede  
✅ Timeout definido (30s)  
✅ Fallback quando API falha  
✅ Mensagens de erro descritivas  

---

## 🎯 Próximos Passos e Melhorias

### Melhorias Planejadas

1. **Paginação**
   - Buscar todas as páginas (não apenas página 0)
   - Configurar tamanho de página dinamicamente

2. **Cache**
   - Salvar resultados em cache local
   - Evitar requisições duplicadas no mesmo dia

3. **Processamento Paralelo**
   - Buscar múltiplos advogados simultaneamente
   - Usar threads ou asyncio

4. **Notificações**
   - Email quando encontrar novas publicações
   - Integração com Telegram/WhatsApp

5. **Histórico**
   - Salvar histórico de buscas
   - Comparar com dias anteriores

6. **Filtros Avançados**
   - Filtrar por tipo de comunicação
   - Filtrar por órgão específico
   - Buscar por número de processo

---

## 📝 Changelog

### Versão 1.0 (2026-02-02)
- ✅ Implementação inicial
- ✅ Suporte a API JSON
- ✅ Fallback para scraping HTML
- ✅ Logging detalhado
- ✅ Tratamento de múltiplos formatos de campos
- ✅ Testes automatizados
- ✅ Documentação completa

---

## 👥 Suporte

### Contato
- **Desenvolvido para:** Edson Pratti Advogados
- **Tecnologias:** Python 3.9+, Requests, BeautifulSoup4
- **Licença:** Uso interno

### Como Reportar Problemas

1. Execute `python3 test_djne.py`
2. Copie o output completo (incluindo DEBUG)
3. Descreva o comportamento esperado vs atual
4. Informe data/hora da tentativa

---

**Última atualização:** 2 de fevereiro de 2026  
**Versão da documentação:** 1.0  
**Status:** ✅ Produção
