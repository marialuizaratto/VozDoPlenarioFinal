# Voz do Plenário - API de Análise de Discursos

API desenvolvida em Python com FastAPI para consumir, processar e analisar dados de discursos de deputados e partidos da Câmara dos Deputados do Brasil.

O projeto oferece uma interface rápida e moderna para explorar a atividade legislativa, gerando visualizações de dados e rankings de performance.

## Arquitetura

A arquitetura do projeto é baseada em um sistema de **cache local** para garantir alta performance e resiliência.

1.  **Coletor de Dados (`download_data.py`)**: Um script independente que consome a API de Dados Abertos da Câmara dos Deputados. Ele baixa e armazena localmente os dados de deputados e seus discursos dos últimos 90 dias em arquivos CSV (`csv_data/deputados.csv` e `csv_data/discursos.csv`).
2.  **API Principal (`main.py` e `services.py`)**: A aplicação FastAPI que lê os dados diretamente dos arquivos CSV cacheados. Toda a lógica de negócio, como filtragem de dados, geração de nuvens de palavras e cálculo de rankings, é executada a partir desses arquivos locais.

Este design desacopla a API da dependência direta e constante da API externa, tornando as respostas muito mais rápidas e permitindo que o serviço funcione mesmo que a API da Câmara esteja instável.

## Funcionalidades

- **Listagem de Deputados e Partidos**: Endpoints para listar todos os deputados ou filtrar por partido.
- **Consulta de Discursos**: Acesso aos discursos de deputados individuais ou de partidos inteiros, com filtros por data.
- **Nuvem de Palavras**: Geração de visualizações (`.png`) com as palavras mais frequentes nos discursos de um deputado ou partido.
- **Rankings de Atividade**:
  - Deputados que mais e menos discursaram.
  - Partidos mais ativos (com base na média de discursos por deputado).

## Tecnologias Utilizadas

- **Backend**: Python
- **Framework**: FastAPI
- **Servidor**: Uvicorn
- **Visualização de Dados**: WordCloud, Matplotlib
- **Processamento de Linguagem Natural**: NLTK (para remoção de stopwords)
- **Requisições HTTP**: httpx (no script de download)

## Como Executar o Projeto

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/vozdoplenariopublica.git
cd vozdoplenariopublica
```

### 2. Instale as Dependências

Crie um ambiente virtual (recomendado) e instale as bibliotecas necessárias:

```bash
# Crie e ative um ambiente virtual (Exemplo para Windows)
python -m venv venv
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### 3. Baixe os Dados (Passo Essencial)

Antes de iniciar a API, você **precisa** criar o cache de dados. Execute o script de download:

```bash
python download_data.py
```

Este comando irá criar o diretório `csv_data/` e preenchê-lo com os dados de deputados e discursos. O processo pode levar alguns minutos.

### 4. Execute a API

Com o cache de dados pronto, inicie o servidor FastAPI:

```bash
uvicorn main:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`.

## Documentação Interativa

Após iniciar o servidor, você pode acessar a documentação interativa (Swagger UI) para testar os endpoints diretamente no seu navegador:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Endpoints da API

### Deputados

- `GET /deputados`: Lista todos os deputados.
- `GET /deputados/{id}`: Retorna os detalhes de um deputado específico.
- `GET /deputados/{id}/discursos`: Lista os discursos de um deputado.
- `GET /deputados/{id}/wordcloud`: Gera uma nuvem de palavras para um deputado.

### Partidos

- `GET /partidos/{sigla}/deputados`: Lista os deputados de um partido.
- `GET /partidos/{sigla}/discursos`: Lista os discursos de um partido.
- `GET /partidos/{sigla}/wordcloud`: Gera uma nuvem de palavras para um partido.

### Rankings

- `GET /ranking/deputados/mais-falam`: Top 50 deputados com mais discursos.
- `GET /ranking/deputados/menos-falam`: Top 50 deputados com menos discursos.
- `GET /ranking/partidos/mais-ativos`: Ranking de partidos por média de discursos.

## Exemplo de Uso com cURL

```bash
# Listar todos os deputados
curl http://127.0.0.1:8000/deputados

# Baixar a nuvem de palavras de um partido
curl "http://127.0.0.1:8000/partidos/PT/wordcloud" --output nuvem_partido_pt.png
```
