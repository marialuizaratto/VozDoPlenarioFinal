
import os
import csv
import logging
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import nltk
from nltk.corpus import stopwords
from fastapi import HTTPException
from datetime import datetime
import groq
from dotenv import load_dotenv
import itertools
import json

# --- Setup ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

DATA_DIR = "csv_data"
DEPUTIES_FILE = os.path.join(DATA_DIR, "deputados.csv")
SPEECHES_FILE = os.path.join(DATA_DIR, "discursos.csv")
PROPOSITIONS_FILE = os.path.join(DATA_DIR, "proposicoes.csv")

# Groq API Keys Round-Robin
GROQ_API_KEYS = [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
]
# Filter out any keys that are not set
GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]
if not GROQ_API_KEYS:
    logging.warning("Nenhuma chave de API da Groq foi encontrada no arquivo .env. A funcionalidade de análise de discursos estará desativada.")
    GROQ_API_KEYS = []

api_key_cycle = itertools.cycle(GROQ_API_KEYS)

# NLTK setup
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

stop_words = set(stopwords.words('portuguese'))

# --- Helper Functions ---

def check_cache_files():
    """Checks if the required CSV files exist."""
    if not all(os.path.exists(f) for f in [DEPUTIES_FILE, SPEECHES_FILE, PROPOSITIONS_FILE]):
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
    if not text:
        logging.warning("Text for word cloud is empty. Skipping generation.")
        # Create a placeholder image indicating no data
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, "Sem dados para gerar a nuvem de palavras", ha='center', va='center')
        plt.axis('off')
        plt.savefig(filepath)
        plt.close()
        return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=stop_words).generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.savefig(filepath)
    plt.close()
    logging.info(f"Word cloud saved to {filepath}")

# --- Groq Analysis Function ---

def analyze_speeches_with_groq(speeches: list, deputy_info: dict):
    """
    Analyzes a list of speeches using the Groq API with a detailed prompt.
    """
    if not GROQ_API_KEYS:
        raise HTTPException(status_code=503, detail="Serviço de análise indisponível. Nenhuma chave de API configurada.")

    if not speeches:
        return {
            "biografia": f"Análise para {deputy_info.get('nome', 'Deputado(a)')}, do partido {deputy_info.get('siglaPartido', 'N/A')}.",
            "nivel_atividade": "Baixo",
            "ranking_topicos": [],
            "analise_detalhada": "Nenhum discurso encontrado para o período selecionado, portanto não há análise a ser feita.",
            "tema_principal": "N/A",
            "nivel_toxicidade": 0
        }

    # Prepare the speeches text
    speeches_text = "\n\n---\n\n".join([
        f"**Discurso em {s.get('dataHoraInicio')} sobre '{s.get('tipoDiscurso')}'**\n"
        f"**Resumo:** {s.get('sumario', 'N/A')}\n\n"
        f"**Transcrição:**\n{s.get('transcricao', 'N/A')}"
        for s in speeches
    ])

    # Truncate if too long to avoid API errors
    if len(speeches_text) > 20000:
        speeches_text = speeches_text[:20000] + "\n\n... (discursos truncados para análise)"

    # Construct the biography string
    bio = (
        f"O(A) deputado(a) {deputy_info.get('nome', '')} (ID: {deputy_info.get('id', '')}), "
        f"filiado(a) ao {deputy_info.get('siglaPartido', 'partido não informado')} "
        f"pelo estado de {deputy_info.get('siglaUf', 'UF não informada')}."
    )

    prompt = f"""
"Você é um analista político sênior, encarregado de redigir uma análise imparcial e detalhada sobre a atuação de um deputado federal com base em seus discursos. Sua análise deve ser completamente neutra, focada em fatos e evidências, evitando elogios ou insultos.

**Instruções Detalhadas:**

1.  **Biografia Inicial:** Com base nos dados a seguir, escreva uma biografia curta e esclarecedora sobre o deputado.
    *   **Dados do Deputado:** {bio}

2.  **Nível de Atividade:** Com base no volume de discursos fornecidos, comente brevemente sobre o nível de atividade do deputado no plenário (ex: 'Alto', 'Médio', 'Baixo').

3.  **Ranking de Tópicos:** Crie um ranking dos 5 tópicos mais abordados pelo deputado nos discursos.

4.  **Análise Aprofundada:**
    *   Para cada um dos tópicos do ranking, descreva a posição do deputado.
    *   **Use exemplos diretos dos discursos (citações curtas) para justificar cada ponto da sua análise.**
    *   Identifique se há um tema de maior destaque ou especialidade para o parlamentar (ex: educação, direitos humanos, agronegócio).

5.  **Nível de Toxicidade:**
    *   No final da análise, atribua um 'nível de toxicidade' de 1 a 100.
    *   **Critério de Toxicidade:** A pontuação deve se basear em linguagem agressiva, ataques pessoais, desinformação ou retórica inflamatória. **Ignore completamente formalidades e polidez** (como 'obrigado', 'senhor', 'senhora') na contagem de toxicidade.

**Formato de Saída OBRIGATÓRIO (JSON Válido):**

Retorne um objeto JSON com as seguintes chaves:
- `biografia`: (string)
- `nivel_atividade`: (string)
- `ranking_topicos`: (array de strings)
- `analise_detalhada`: (string com a análise aprofundada e citações)
- `tema_principal`: (string)
- `nivel_toxicidade`: (integer de 1 a 100)

**Discursos para Análise:**
{speeches_text}
"
"""
    try:
        api_key = next(api_key_cycle)
        client = groq.Groq(api_key=api_key)

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.2,
            max_tokens=2048, # Increased token limit for more detailed analysis
            response_format={"type": "json_object"},
        )

        analysis_content = chat_completion.choices[0].message.content
        return json.loads(analysis_content)

    except groq.APIError as e:
        logging.error(f"Erro na API da Groq: {e}")
        raise HTTPException(status_code=503, detail=f"Erro ao comunicar com o serviço de análise: {e}")
    except json.JSONDecodeError:
        logging.error("Erro ao decodificar a resposta JSON da API Groq.")
        raise HTTPException(status_code=500, detail="Resposta inválida do serviço de análise.")
    except Exception as e:
        logging.error(f"Erro inesperado na análise de discursos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no serviço de análise.")


# --- Core Service Functions (now synchronous and CSV-based) ---

def get_all_deputies():
    """Fetches a list of all deputies from the CSV cache."""
    check_cache_files()
    return read_csv_data(DEPUTIES_FILE)

def get_deputy_by_id(deputy_id: int):
    """Finds a single deputy by ID from the CSV cache."""
    all_deputies = get_all_deputies()
    for deputy in all_deputies:
        if int(deputy.get('id', 0)) == deputy_id:
            return deputy
    return None

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
    deputy_details = get_deputy_by_id(deputy_id)
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

# The analyze_deputy_profile function is removed as it requires live data and a powerful LLM,
# which complicates the cached data model. It can be added back if needed with significant changes.
