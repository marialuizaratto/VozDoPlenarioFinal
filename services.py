import os
import csv
import logging
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import nltk
from fastapi import HTTPException
from datetime import datetime, timedelta
import httpx

# --- Setup ---
logging.basicConfig(level=logging.INFO)

DATA_DIR = "csv_data"
DEPUTIES_FILE = os.path.join(DATA_DIR, "deputados.csv")
SPEECHES_FILE = os.path.join(DATA_DIR, "discursos.csv")

# Cache interno das stopwords (carregado sob demanda, não na importação do módulo).
# Isso evita atraso na inicialização do servidor, que pode fazer o health check
# do Render falhar caso o download do NLTK demore.
_stop_words = None


def _get_stop_words():
    global _stop_words
    if _stop_words is None:
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        from nltk.corpus import stopwords
        base_stopwords = set(stopwords.words('portuguese'))

        # Palavras comuns em discursos parlamentares que não agregam
        # significado à nuvem de palavras (jargão, formalidades, verbos
        # genéricos, etc.)
        additional_stopwords = {
            'obrigado', 'obrigada', 'presidente', 'senhor', 'senhora', 'sr', 'sra',
            'deputado', 'deputada', 'excelência', 'vossa', 'câmara', 'casa',
            'ele', 'ela', 'eles', 'elas', 'hoje', 'governo', 'menos', 'mais',
            'ano', 'anos', 'ordem', 'orador', 'oradora', 'vai', 'vão', 'foi',
            'foram', 'pessoa', 'pessoas', 'fazer', 'porque', 'acho', 'acha',
            'sim', 'não', 'nao', 'aqui', 'agora', 'ontem', 'vez', 'vezes',
            'ser', 'estar', 'ter', 'poder', 'querer', 'ir', 'sobre', 'ainda',
            'até', 'entre', 'sem', 'isso', 'só', 'pode', 'bem', 'assim',
            'então', 'muito', 'muita', 'muitos', 'muitas', 'toda', 'todo',
            'todas', 'todos', 'nós', 'aquele', 'aquela', 'aqueles', 'aquelas',
        }

        _stop_words = base_stopwords | additional_stopwords
    return _stop_words

# --- Date Filter Setup ---
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=45)

# --- Groq (Análise de IA) Setup ---
# Suporta múltiplas chaves para revezar entre elas: se uma bater o limite de
# uso gratuito (rate limit) ou falhar, a próxima é tentada automaticamente.
GROQ_API_KEYS = [
    key for key in [
        os.environ.get("GROQ_API_KEY"),
        os.environ.get("GROQ_API_KEY_1"),
        os.environ.get("GROQ_API_KEY_2"),
        os.environ.get("GROQ_API_KEY_3"),
    ] if key
]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

# --- Helper Functions ---

def check_cache_files():
    """Checks if the required CSV files exist."""
    if not all(os.path.exists(f) for f in [DEPUTIES_FILE, SPEECHES_FILE]):
        raise HTTPException(
            status_code=503,
            detail="Data cache not found. Please run the `download_data.py` script first."
        )

def read_csv_data(filepath: str):
    """Reads all rows from a given CSV file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        logging.error(f"Cache file not found: {filepath}")
        return []

def generate_wordcloud(text: str, filepath: str):
    """Generates and saves a word cloud image from text."""
    if not text or not text.strip():
        logging.warning("Text for word cloud is empty. Skipping generation.")
        # Create a placeholder image indicating no data
        plt.figure(figsize=(10, 5))
        plt.text(
            0.5, 0.5,
            "Este(a) deputado(a) não possui discursos registrados\nno período analisado.",
            ha='center', va='center', fontsize=14, wrap=True
        )
        plt.axis('off')
        plt.savefig(filepath)
        plt.close()
        return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=_get_stop_words()).generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.savefig(filepath)
    plt.close()
    logging.info(f"Word cloud saved to {filepath}")

# --- Core Service Functions (now synchronous and CSV-based) ---

def get_all_deputies():
    """Fetches a list of all deputies from the CSV cache."""
    check_cache_files()
    return read_csv_data(DEPUTIES_FILE)

def get_deputies_by_party(sigla: str):
    """Fetches a list of deputies from a specific party from the CSV cache."""
    all_deputies = get_all_deputies()
    filtered_deputies = [d for d in all_deputies if d.get('siglaPartido', '').upper() == sigla.upper()]
    if not filtered_deputies:
        raise HTTPException(status_code=404, detail=f"No deputies found for party '{sigla}'.")
    return filtered_deputies

def get_deputy_speeches(deputy_id: int, data_inicio: str = None, data_fim: str = None):
    """Fetches speeches for a given deputy from the CSV cache, optionally filtered by date."""
    check_cache_files()
    all_speeches = read_csv_data(SPEECHES_FILE)

    # Note: The CSV stores deputy IDs as strings
    deputy_id_str = str(deputy_id)
    filtered_speeches = [s for s in all_speeches if s.get('idDeputado') == deputy_id_str]

    if data_inicio:
        start_date = datetime.strptime(data_inicio, '%Y-%m-%d')
        filtered_speeches = [s for s in filtered_speeches if datetime.strptime(s['dataHoraInicio'][:10], '%Y-%m-%d') >= start_date]

    if data_fim:
        end_date = datetime.strptime(data_fim, '%Y-%m-%d')
        filtered_speeches = [s for s in filtered_speeches if datetime.strptime(s['dataHoraInicio'][:10], '%Y-%m-%d') <= end_date]

    return filtered_speeches

def get_speeches_by_party(sigla: str, data_inicio: str = None, data_fim: str = None):
    """Fetches speeches from all deputies of a specific party from the CSV cache."""
    deputies_in_party = get_deputies_by_party(sigla)
    deputy_ids = {d['id'] for d in deputies_in_party}

    check_cache_files()
    all_speeches = read_csv_data(SPEECHES_FILE)

    party_speeches = [s for s in all_speeches if s.get('idDeputado') in deputy_ids]

    if data_inicio:
        start_date = datetime.strptime(data_inicio, '%Y-%m-%d')
        party_speeches = [s for s in party_speeches if datetime.strptime(s['dataHoraInicio'][:10], '%Y-%m-%d') >= start_date]

    if data_fim:
        end_date = datetime.strptime(data_fim, '%Y-%m-%d')
        party_speeches = [s for s in party_speeches if datetime.strptime(s['dataHoraInicio'][:10], '%Y-%m-%d') <= end_date]

    return party_speeches

def get_deputy_details_and_generate_wordcloud(deputy_id: int):
    """Generates a word cloud for a deputy using speech data from the CSV cache."""
    all_deputies = get_all_deputies()
    deputy_details = next((d for d in all_deputies if int(d.get('id', 0)) == deputy_id), None)

    if not deputy_details:
        raise HTTPException(status_code=404, detail="Deputy not found.")

    # Use speeches for the word cloud
    deputy_speeches = get_deputy_speeches(deputy_id)

    # Combine 'sumario' and 'transcricao' for the text
    text_for_wordcloud = ' '.join([
        s.get('sumario', '') + ' ' + s.get('transcricao', '')
        for s in deputy_speeches
    ])

    wordcloud_path = os.path.join("cache_perfis", f"wordcloud_{deputy_id}.png")
    if not os.path.exists(wordcloud_path):
        generate_wordcloud(text_for_wordcloud, wordcloud_path)

    deputy_details["wordcloud_url"] = f"/deputados/{deputy_id}/wordcloud"
    return deputy_details

def get_party_details_and_generate_wordcloud(sigla: str):
    """Generates a word cloud for a party using speech data from the CSV cache."""
    deputies_in_party = get_deputies_by_party(sigla)

    # Use speeches for the word cloud
    party_speeches = get_speeches_by_party(sigla)

    text_for_wordcloud = ' '.join([
        s.get('sumario', '') + ' ' + s.get('transcricao', '')
        for s in party_speeches
    ])

    wordcloud_path = os.path.join("cache_perfis", f"wordcloud_party_{sigla}.png")
    if not os.path.exists(wordcloud_path):
        generate_wordcloud(text_for_wordcloud, wordcloud_path)

    return {
        "sigla": sigla,
        "total_deputados": len(deputies_in_party),
        "wordcloud_url": f"/partidos/{sigla}/wordcloud"
    }


# --- Ranking Functions ---

def get_deputy_speech_counts():
    """
    Counts the number of speeches for each deputy.
    """
    check_cache_files()
    all_speeches = read_csv_data(SPEECHES_FILE)
    all_deputies = read_csv_data(DEPUTIES_FILE)

    speech_counts = Counter(s['idDeputado'] for s in all_speeches)

    deputy_speech_list = []
    for deputy in all_deputies:
        deputy_id = deputy['id']
        deputy_speech_list.append({
            "id": deputy_id,
            "nome": deputy.get('nome'),
            "siglaPartido": deputy.get('siglaPartido'),
            "siglaUf": deputy.get('siglaUf'),
            "urlFoto": deputy.get('urlFoto'),
            "speech_count": speech_counts.get(deputy_id, 0)
        })

    return deputy_speech_list

def get_deputy_ranking(order: str = 'most'):
    """
    Gets a ranking of deputies by speech count.
    :param order: 'most' for most speeches, 'least' for least speeches.
    """
    deputy_counts = get_deputy_speech_counts()

    if order == 'most':
        sorted_deputies = sorted(deputy_counts, key=lambda x: x['speech_count'], reverse=True)
    elif order == 'least':
        sorted_deputies = sorted(deputy_counts, key=lambda x: x['speech_count'])
    else:
        raise ValueError("Order must be 'most' or 'least'")

    return sorted_deputies[:50]

def get_party_activity_ranking():
    """
    Calculates and ranks party activity based on the average number of speeches per deputy.
    """
    check_cache_files()
    all_deputies = read_csv_data(DEPUTIES_FILE)
    all_speeches = read_csv_data(SPEECHES_FILE)

    # 1. Count deputies per party
    party_deputy_counts = Counter(d['siglaPartido'] for d in all_deputies if d.get('siglaPartido'))

    # 2. Create a map from deputy ID to party
    deputy_to_party_map = {d['id']: d['siglaPartido'] for d in all_deputies if d.get('id') and d.get('siglaPartido')}

    # 3. Count speeches per party
    party_speech_counts = Counter()
    for speech in all_speeches:
        deputy_id = speech.get('idDeputado')
        party = deputy_to_party_map.get(deputy_id)
        if party:
            party_speech_counts[party] += 1

    # 4. Calculate proportional ranking
    party_ranking = []
    for party, num_deputies in party_deputy_counts.items():
        total_speeches = party_speech_counts.get(party, 0)
        proportional_activity = total_speeches / num_deputies if num_deputies > 0 else 0
        party_ranking.append({
            "siglaPartido": party,
            "total_deputados": num_deputies,
            "total_discursos": total_speeches,
            "media_discursos_por_deputado": round(proportional_activity, 2)
        })

    # 5. Sort by proportional activity
    sorted_ranking = sorted(party_ranking, key=lambda x: x['media_discursos_por_deputado'], reverse=True)

    return sorted_ranking


# --- AI Analysis (Groq) ---

def analyze_deputy_profile(deputy_id: int) -> dict:
    """
    Gera uma análise em texto do perfil de um deputado com base nos seus
    discursos mais recentes, usando a API da Groq (modelo Llama).
    """
    if not GROQ_API_KEYS:
        logging.error("Nenhuma GROQ_API_KEY configurada nas variáveis de ambiente.")
        raise HTTPException(
            status_code=503,
            detail="Análise de IA não disponível no momento."
        )

    all_deputies = get_all_deputies()
    deputy_details = next((d for d in all_deputies if int(d.get('id', 0)) == deputy_id), None)
    if not deputy_details:
        raise HTTPException(status_code=404, detail="Deputy not found.")

    speeches = get_deputy_speeches(deputy_id)
    if not speeches:
        raise HTTPException(
            status_code=404,
            detail="Este deputado não possui discursos registrados no período analisado."
        )

    # Usa até 20 discursos mais recentes para dar mais material à análise,
    # sem estourar o limite de tokens do modelo
    recent_speeches = speeches[-20:]
    texto_discursos = "\n\n".join([
        f"- {(s.get('transcricao') or s.get('sumario') or '')[:1500]}"
        for s in recent_speeches if (s.get('transcricao') or s.get('sumario'))
    ])

    if not texto_discursos.strip():
        raise HTTPException(
            status_code=404,
            detail="Não há conteúdo textual suficiente nos discursos para gerar uma análise."
        )

    prompt = (
        f"Você é um analista político imparcial. Analise os discursos abaixo, feitos pelo(a) "
        f"deputado(a) {deputy_details.get('nome')} ({deputy_details.get('siglaPartido')}-{deputy_details.get('siglaUf')}), "
        f"e responda EXCLUSIVAMENTE com um objeto JSON válido (sem markdown, sem texto fora do JSON), "
        f"seguindo exatamente este formato:\n\n"
        f'{{\n'
        f'  "temas_principais": ["tema 1", "tema 2", "tema 3"],\n'
        f'  "usa_palavrao": true ou false,\n'
        f'  "exemplos_linguagem_informal": ["trecho curto, se houver"],\n'
        f'  "nota_toxicidade": número inteiro de 0 a 100,\n'
        f'  "justificativa_toxicidade": "explicação curta da nota, em até 2 frases",\n'
        f'  "analise_detalhada": "análise completa e neutra do perfil do(a) deputado(a) com base nos discursos, em até 200 palavras"\n'
        f'}}\n\n'
        f"Regras importantes:\n"
        f"- \"temas_principais\": até 5 temas/assuntos mais recorrentes nos discursos.\n"
        f"- \"usa_palavrao\": true apenas se houver palavrões ou xingamentos explícitos no texto.\n"
        f"- \"nota_toxicidade\": 0 = discurso sempre respeitoso e institucional; 100 = extremamente agressivo, "
        f"ofensivo ou desrespeitoso. Avalie o TOM (agressividade, ataques pessoais, desrespeito), não a posição política.\n"
        f"- Não invente informações que não estejam nos textos abaixo.\n"
        f"- Seja imparcial: não julgue o mérito político, apenas o conteúdo e o tom.\n\n"
        f"Discursos:\n{texto_discursos}"
    )

    analise_texto = None
    last_error = None

    for i, api_key in enumerate(GROQ_API_KEYS):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 700,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()
                analise_texto = data["choices"][0]["message"]["content"].strip()
                break  # deu certo, não precisa tentar as próximas chaves
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 429:
                # Limite de uso atingido nesta chave: tenta a próxima
                logging.warning(f"Chave Groq #{i + 1} atingiu o limite de uso, tentando a próxima...")
                continue
            else:
                logging.error(f"Erro da API Groq (chave #{i + 1}) para o deputado {deputy_id}: status={e.response.status_code} body={e.response.text}")
                continue
        except Exception as e:
            last_error = e
            logging.error(f"Erro ao chamar a API da Groq (chave #{i + 1}) para o deputado {deputy_id}: {e}")
            continue

    if analise_texto is None:
        logging.error(f"Todas as chaves Groq falharam para o deputado {deputy_id}: {last_error}")
        raise HTTPException(
            status_code=503,
            detail="Análise de IA não disponível no momento."
        )

    # Tenta interpretar a resposta como JSON estruturado. Se o modelo não
    # seguir o formato pedido por algum motivo, cai num formato de texto simples.
    import json as _json
    try:
        analise_json = _json.loads(analise_texto)
        resultado = {
            "id": deputy_id,
            "nome": deputy_details.get('nome'),
            "siglaPartido": deputy_details.get('siglaPartido'),
            "temas_principais": analise_json.get("temas_principais", []),
            "usa_palavrao": analise_json.get("usa_palavrao", False),
            "exemplos_linguagem_informal": analise_json.get("exemplos_linguagem_informal", []),
            "nota_toxicidade": analise_json.get("nota_toxicidade"),
            "justificativa_toxicidade": analise_json.get("justificativa_toxicidade", ""),
            "analise_detalhada": analise_json.get("analise_detalhada", ""),
            "baseada_em_discursos": len(recent_speeches),
        }
    except (ValueError, AttributeError):
        logging.warning(f"Resposta da Groq para o deputado {deputy_id} não veio em JSON válido. Retornando como texto simples.")
        resultado = {
            "id": deputy_id,
            "nome": deputy_details.get('nome'),
            "siglaPartido": deputy_details.get('siglaPartido'),
            "analise": analise_texto,
            "baseada_em_discursos": len(recent_speeches),
        }

    return resultado
