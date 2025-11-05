# API da Câmara dos Deputados - Análise de Discursos

API desenvolvida em Python com FastAPI para análise de discursos de deputados e partidos da Câmara dos Deputados do Brasil.

## Funcionalidades

1. **Listar discursos por deputado** - Obter todos os discursos de um deputado específico
2. **Listar discursos por partido** - Obter todos os discursos de deputados de um partido
3. **Nuvem de palavras por deputado** - Gerar visualização de palavras mais frequentes nos discursos de um deputado
4. **Nuvem de palavras por partido** - Gerar visualização de palavras mais frequentes nos discursos de um partido

## Tecnologias Utilizadas

- **FastAPI**: Framework web moderno e rápido para construção de APIs
- **httpx**: Cliente HTTP assíncrono para fazer requisições à API da Câmara
- **WordCloud**: Biblioteca para geração de nuvens de palavras
- **NLTK**: Natural Language Toolkit para processamento de linguagem natural (remoção de stopwords)
- **Matplotlib**: Visualização de dados
- **Pillow**: Processamento de imagens

## Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passos

1. Clone ou baixe este repositório

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. (Recomendado) Execute o script de configuração inicial para baixar os dados do NLTK:

```bash
python setup.py
```

Este passo é opcional - se não executado, os dados serão baixados automaticamente na primeira vez que a API for iniciada.

## Como Executar

Execute o servidor da API com o seguinte comando:

```bash
uvicorn main:app --reload
```

Ou simplesmente:

```bash
python main.py
```

A API estará disponível em: `http://localhost:8000`

## Documentação Interativa

Após iniciar o servidor, acesse:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints Disponíveis

### 1. Listar todos os deputados

```
GET /deputados
```

**Resposta:**
```json
{
  "total": 513,
  "deputados": [
    {
      "id": 123,
      "nome": "Nome do Deputado",
      "siglaPartido": "PT",
      "siglaUf": "SP",
      ...
    }
  ]
}
```

### 2. Obter informações de um deputado

```
GET /deputados/{deputy_id}
```

**Exemplo:**
```
GET /deputados/204554
```

### 3. Listar discursos de um deputado

```
GET /deputados/{deputy_id}/discursos?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD
```

**Parâmetros de consulta opcionais:**
- `data_inicio`: Data inicial no formato YYYY-MM-DD
- `data_fim`: Data final no formato YYYY-MM-DD

**Exemplo:**
```
GET /deputados/204554/discursos?data_inicio=2024-01-01&data_fim=2024-12-31
```

**Resposta:**
```json
{
  "deputado": {
    "id": 204554,
    "nome": "Nome Completo",
    "nomeEleitoral": "Nome Eleitoral",
    "partido": "PT",
    "uf": "SP"
  },
  "total_discursos": 45,
  "filtros": {
    "data_inicio": "2024-01-01",
    "data_fim": "2024-12-31"
  },
  "discursos": [...]
}
```

### 4. Gerar nuvem de palavras de um deputado

```
GET /deputados/{deputy_id}/wordcloud?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD&width=800&height=600
```

**Parâmetros de consulta opcionais:**
- `data_inicio`: Data inicial no formato YYYY-MM-DD
- `data_fim`: Data final no formato YYYY-MM-DD
- `width`: Largura da imagem (padrão: 800)
- `height`: Altura da imagem (padrão: 600)

**Exemplo:**
```
GET /deputados/204554/wordcloud?data_inicio=2024-01-01&width=1000&height=800
```

**Resposta:** Imagem PNG da nuvem de palavras

### 5. Listar deputados de um partido

```
GET /partidos/{sigla}/deputados
```

**Exemplo:**
```
GET /partidos/PT/deputados
```

**Resposta:**
```json
{
  "partido": "PT",
  "total_deputados": 68,
  "deputados": [...]
}
```

### 6. Listar discursos de um partido

```
GET /partidos/{sigla}/discursos?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD
```

**Parâmetros de consulta opcionais:**
- `data_inicio`: Data inicial no formato YYYY-MM-DD
- `data_fim`: Data final no formato YYYY-MM-DD

**Exemplo:**
```
GET /partidos/PT/discursos?data_inicio=2024-01-01&data_fim=2024-12-31
```

**Resposta:**
```json
{
  "partido": "PT",
  "total_discursos": 1523,
  "filtros": {
    "data_inicio": "2024-01-01",
    "data_fim": "2024-12-31"
  },
  "discursos": [
    {
      "deputado": {
        "id": 123,
        "nome": "Nome do Deputado",
        "siglaPartido": "PT",
        "siglaUf": "SP"
      },
      "transcricao": "...",
      "sumario": "...",
      ...
    }
  ]
}
```

### 7. Gerar nuvem de palavras de um partido

```
GET /partidos/{sigla}/wordcloud?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD&width=800&height=600
```

**Parâmetros de consulta opcionais:**
- `data_inicio`: Data inicial no formato YYYY-MM-DD
- `data_fim`: Data final no formato YYYY-MM-DD
- `width`: Largura da imagem (padrão: 800)
- `height`: Altura da imagem (padrão: 600)

**Exemplo:**
```
GET /partidos/PT/wordcloud?width=1200&height=900
```

**Resposta:** Imagem PNG da nuvem de palavras

## Exemplos de Uso

### Usando cURL

```bash
# Listar todos os deputados
curl http://localhost:8000/deputados

# Obter discursos de um deputado específico
curl "http://localhost:8000/deputados/204554/discursos?data_inicio=2024-01-01"

# Baixar nuvem de palavras de um deputado
curl "http://localhost:8000/deputados/204554/wordcloud" --output wordcloud_deputado.png

# Baixar nuvem de palavras de um partido
curl "http://localhost:8000/partidos/PT/wordcloud" --output wordcloud_partido.png
```

### Usando Python

```python
import requests
from PIL import Image
from io import BytesIO

# Listar discursos de um deputado
response = requests.get(
    "http://localhost:8000/deputados/204554/discursos",
    params={"data_inicio": "2024-01-01", "data_fim": "2024-12-31"}
)
discursos = response.json()
print(f"Total de discursos: {discursos['total_discursos']}")

# Obter e exibir nuvem de palavras
response = requests.get("http://localhost:8000/deputados/204554/wordcloud")
if response.status_code == 200:
    image = Image.open(BytesIO(response.content))
    image.show()
```

### Usando JavaScript/Fetch

```javascript
// Listar discursos de um partido
fetch('http://localhost:8000/partidos/PT/discursos?data_inicio=2024-01-01')
  .then(response => response.json())
  .then(data => {
    console.log(`Total de discursos: ${data.total_discursos}`);
    console.log(data.discursos);
  });

// Exibir nuvem de palavras em uma imagem HTML
fetch('http://localhost:8000/partidos/PT/wordcloud')
  .then(response => response.blob())
  .then(blob => {
    const imageUrl = URL.createObjectURL(blob);
    document.getElementById('wordcloud').src = imageUrl;
  });
```

## Estrutura do Projeto

```
ProjetoAPI_FGV/
├── main.py              # Aplicação principal FastAPI com os endpoints
├── services.py          # Serviços para interação com a API da Câmara
├── utils.py             # Utilitários para processamento de texto e nuvem de palavras
├── setup.py             # Script de configuração inicial (baixa dados do NLTK)
├── tests.py             # Suite de testes para validar a API
├── requirements.txt     # Dependências do projeto
├── PROJETO.md          # Descrição do projeto
├── ENDPOINTS.md        # Documentação dos endpoints da API da Câmara
├── README.md           # Este arquivo
└── .gitignore          # Arquivos a serem ignorados pelo Git
```

## API da Câmara dos Deputados

Este projeto consome a API oficial de dados abertos da Câmara dos Deputados:
- URL Base: https://dadosabertos.camara.leg.br/api/v2/
- Documentação: https://dadosabertos.camara.leg.br/swagger/api.html

## Observações

- **Primeira execução**: Na primeira vez que a API for iniciada, o NLTK irá baixar automaticamente o corpus de stopwords em português (aproximadamente 500KB). Isso é feito apenas uma vez.
- A geração de nuvens de palavras para partidos pode demorar alguns minutos, pois precisa buscar os discursos de todos os deputados do partido
- As stopwords (palavras comuns que são filtradas) são obtidas do NLTK e incluem termos específicos do contexto político brasileiro (ex: "senhor", "presidente", "câmara")
- Recomenda-se usar filtros de data para melhorar a performance das requisições

## Autor

Desenvolvido como parte do Projeto API FGV

## Licença

Este projeto é de código aberto e está disponível para fins educacionais.
