# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

API FastAPI para consulta e análise de discursos de deputados da Câmara dos Deputados do Brasil. Consome a API de Dados Abertos da Câmara (`https://dadosabertos.camara.leg.br/api/v2`) e expõe dados processados via endpoints REST.

## Comandos

### Setup inicial (uma vez)
```bash
pip install -r requirements.txt
python setup.py          # Baixa stopwords do NLTK
python download_data.py  # Popula csv_data/ com deputados e discursos (pode levar minutos)
```

### Rodar a API
```bash
uvicorn main:app --reload
# Disponível em http://127.0.0.1:8000
# Swagger UI em http://127.0.0.1:8000/docs
```

### Testes
```bash
# Testes unitários/integração com pytest (não requerem API rodando)
pytest test_main.py test_rankings.py test_integration.py -v

# Teste de integração manual (requer API rodando em localhost:8000)
python tests.py
```

## Arquitetura

### Fluxo de dados (offline-first)

A API **nunca** consulta a Câmara diretamente em tempo de request. O ciclo é:

1. `download_data.py` → consulta API da Câmara → salva `csv_data/deputados.csv` e `csv_data/discursos.csv`
2. `main.py` (rotas) → `services.py` (lógica) → lê os CSVs locais

Este desacoplamento é intencional: garante respostas rápidas e resiliência quando a API externa está instável.

### Módulos principais

- **`main.py`** — Rotas FastAPI. Delega toda lógica para `services.py`. Cria diretórios `cache_perfis/` e `csv_data/` na inicialização.
- **`services.py`** — Toda a lógica de negócio: leitura de CSVs, filtros de data, geração de wordclouds (salvas em `cache_perfis/`), rankings.
- **`utils.py`** — Utilitários de processamento de texto: `clean_text()`, `extract_text_from_speeches()`, `generate_wordcloud_image()` (retorna bytes), `load_cache()` / `save_cache()` para JSON.
- **`download_data.py`** — Script standalone de coleta. Pagina pela API da Câmara e escreve CSVs. Tem retry automático em falhas HTTP.

### Wordclouds

- `services.generate_wordcloud()` salva PNGs em `cache_perfis/wordcloud_{deputy_id}.png` e `cache_perfis/wordcloud_party_{sigla}.png`.
- `utils.generate_wordcloud_image()` retorna `bytes` diretamente (sem salvar), usada em contextos diferentes.
- Stopwords customizadas para contexto político estão em `utils.STOPWORDS_PT` (ex: "senhor", "presidente", "deputado").

### Campos do CSV de discursos

O CSV `discursos.csv` tem a coluna `idDeputado` adicionada pelo `download_data.py` (não existe na API original). Os campos de texto usados para wordcloud são `sumario` e `transcricao`. Datas ficam em `dataHoraInicio` no formato `YYYY-MM-DDTHH:MM:SS`.

### Atenção: scripts legados

`gerar_cache_discursos.py` e `gerar_cache_ranking.py` usam `await` em funções que agora são síncronas em `services.py` — estão desatualizados e não funcionam com a versão atual. `test_main.py` também referencia endpoints e integrações (Groq, `/analise/`, `/wordcloud/deputado/{id}.png`) que foram removidos.

## Configuração de ambiente

Não há variáveis de ambiente obrigatórias na versão atual. O arquivo `runtime.txt` especifica a versão do Python (`python-3.11`).
