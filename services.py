import os
import httpx
import logging
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from fastapi import HTTPException
from dotenv import load_dotenv
from groq import Groq
import time
import json
import re
import glob
from datetime import datetime, timedelta

def setup_logging():
    """Configures logging for the application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Setup
load_dotenv()
setup_logging()

# NLTK setup
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

stop_words = set(stopwords.words('portuguese'))

# API Keys and Client Management
GROQ_API_KEYS = [
    os.environ.get("GROQ_API_KEY_1"),
    os.environ.get("GROQ_API_KEY_2"),
    os.environ.get("GROQ_API_KEY_3"),
]
GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key] # Filter out None values
if not GROQ_API_KEYS:
    logging.warning("GROQ_API_KEYS environment variable not set or empty.")
    
current_key_index = 0

def get_groq_client():
    global current_key_index
    if not GROQ_API_KEYS:
        raise ValueError("No GROQ API keys available.")
    api_key = GROQ_API_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(GROQ_API_KEYS)
    return Groq(api_key=api_key)

# --- Helper Functions ---

async def fetch_data(url: str):
    """Fetches data from a given URL with retry logic."""
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.ReadTimeout:
            logging.error(f"Timeout error fetching data from {url}")
            raise HTTPException(status_code=504, detail=f"Gateway timeout: The request to {url} timed out.")
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error fetching data from {url}: {e.response.status_code}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch data from external API: {e.response.text}")
        except Exception as e:
            logging.error(f"An unexpected error occurred when fetching data from {url}: {e}")
            raise HTTPException(status_code=500, detail="An internal error occurred while fetching external data.")

def generate_wordcloud(text: str, filepath: str):
    """Generates and saves a word cloud image from text."""
    if not text:
        logging.warning("Text for word cloud is empty. Skipping generation.")
        return
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=stop_words).generate(text)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.savefig(filepath)
        plt.close()
        logging.info(f"Word cloud saved to {filepath}")
    except Exception as e:
        logging.error(f"Failed to generate word cloud: {e}")

# --- Core Service Functions ---

def get_toxicity_ranking():
    """Reads cached analysis files, extracts toxicity scores, and returns a ranked list."""
    ranking = []
    cache_files = glob.glob(os.path.join("cache_perfis", "analise_*.json"))

    for file_path in cache_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                analysis_text = data.get("analysis", "")

                # Extract deputy ID from filename
                deputy_id_match = re.search(r'analise_(\d+).json', os.path.basename(file_path))
                if not deputy_id_match:
                    continue
                deputy_id = int(deputy_id_match.group(1))

                # Extract toxicity score
                score_match = re.search(r"Nível de Toxicidade \(0 a 100\):.*?(\d+)", analysis_text, re.DOTALL)
                score = int(score_match.group(1)) if score_match else 0

                # Extract deputy name (best effort)
                name_match = re.search(r"Deputado\(a\):\s*(.*?)\n", analysis_text)
                name = name_match.group(1).strip() if name_match else f"Deputado {deputy_id}"

                ranking.append({
                    "id": deputy_id,
                    "nome": name,
                    "toxicity_score": score
                })
        except (json.JSONDecodeError, IndexError, Exception) as e:
            logging.error(f"Failed to process analysis file {file_path}: {e}")
            continue

    # Sort by toxicity score, descending
    return sorted(ranking, key=lambda x: x['toxicity_score'], reverse=True)

async def get_all_deputies():
    """Fetches a list of all deputies."""
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados?ordem=ASC&ordenarPor=nome"
    all_deputies = []
    page = 1
    while True:
        try:
            response = await fetch_data(f"{url}&pagina={page}&itens=100")
            deputies = response.get("dados", [])
            if not deputies:
                break
            all_deputies.extend(deputies)
            page += 1
        except HTTPException as e:
            logging.error(f"Error fetching page {page} of deputies: {e.detail}")
            break
    return all_deputies

async def get_deputy_speeches(deputy_id: int, data_inicio: str, data_fim: str):

    """Fetches speeches for a given deputy within a date range."""

    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputy_id}/discursos?dataInicio={data_inicio}&dataFim={data_fim}&ordenarPor=dataHoraInicio&ordem=ASC"

    all_speeches = []

    page = 1

    while True:

        try:

            response = await fetch_data(f"{url}&pagina={page}&itens=100")

            speeches = response.get("dados", [])

            if not speeches:

                break

            all_speeches.extend(speeches)

            page += 1

        except HTTPException as e:

            logging.error(f"Error fetching page {page} of speeches for deputy {deputy_id}: {e.detail}")

            break

    return all_speeches





async def get_deputies_by_party(sigla: str):
    """Fetches a list of all deputies from a specific party."""
    all_deputies = await get_all_deputies()
    filtered_deputies = []
    for deputy in all_deputies:
        if deputy.get('siglaPartido') and deputy['siglaPartido'].upper() == sigla.upper():
            filtered_deputies.append(deputy)
    if not filtered_deputies:
        raise HTTPException(status_code=404, detail=f"No deputies found for party '{sigla}'.")
    return filtered_deputies





async def get_speeches_by_party(sigla: str, data_inicio: str, data_fim: str):

    """Fetches speeches from all deputies of a specific party within a date range."""

    deputies = await get_deputies_by_party(sigla)

    all_speeches = []

    for deputy in deputies:

        speeches = await get_deputy_speeches(deputy['id'], data_inicio, data_fim)

        all_speeches.extend(speeches)

    return all_speeches







def get_speech_ranking(order: str = 'desc'):
    """Reads speech count data and returns a ranked list of deputies."""
    try:
        with open(os.path.join("cache_geral", "discursos_deputados.json"), 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Speech count cache not found. Please run gerar_cache_discursos.py first.")

    reverse = True if order == 'desc' else False
    return sorted(data, key=lambda x: x.get('speech_count', 0), reverse=reverse)

def get_party_speech_ranking():
    """Calculates the average speech count per party and returns a ranked list."""
    try:
        with open(os.path.join("cache_geral", "discursos_deputados.json"), 'r', encoding='utf-8') as f:
            deputies_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Speech count cache not found. Please run gerar_cache_discursos.py first.")

    party_speech_counts = {}
    party_deputy_counts = {}

    for deputy in deputies_data:
        party = deputy.get('siglaPartido')
        speech_count = deputy.get('speech_count', 0)
        if party:
            party_speech_counts.setdefault(party, 0)
            party_speech_counts[party] += speech_count
            party_deputy_counts.setdefault(party, 0)
            party_deputy_counts[party] += 1

    party_ranking = []
    for party, total_speeches in party_speech_counts.items():
        deputy_count = party_deputy_counts.get(party, 0)
        average_speeches = total_speeches / deputy_count if deputy_count > 0 else 0
        party_ranking.append({
            "siglaPartido": party,
            "totalDiscursos": total_speeches,
            "numeroDeputados": deputy_count,
            "mediaDiscursosPorDeputado": average_speeches
        })

    return sorted(party_ranking, key=lambda x: x['mediaDiscursosPorDeputado'], reverse=True)


async def get_deputy_details_and_generate_wordcloud(deputy_id: int):
    """
    Busca detalhes de um deputado e gera a nuvem de palavras de suas proposições.
    """
    logging.info(f"Fetching details for deputy {deputy_id}")
    deputy_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputy_id}"
    props_url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes?idDeputadoAutor={deputy_id}&ordem=ASC&ordenarPor=id"

    deputy_data = await fetch_data(deputy_url)
    propositions_data = await fetch_data(props_url)

    if not deputy_data.get("dados"):
        raise HTTPException(status_code=404, detail="Deputy not found.")

    text_for_wordcloud = ' '.join([prop['ementa'] for prop in propositions_data.get('dados', []) if prop.get('ementa')])
    wordcloud_path = os.path.join("cache_perfis", f"wordcloud_{deputy_id}.png")
    generate_wordcloud(text_for_wordcloud, wordcloud_path)

    deputy_details = deputy_data["dados"]
    deputy_details["wordcloud_url"] = f"/wordcloud/deputado/{deputy_id}.png"
    
    return deputy_details

async def get_party_details_and_generate_wordcloud(party_initials: str):
    """
    Busca detalhes de um partido e gera a nuvem de palavras das proposições de seus membros.
    """
    logging.info(f"Fetching details for party {party_initials}")
    
    # 1. Get party ID
    parties_url = "https://dadosabertos.camara.leg.br/api/v2/partidos?ordem=ASC&ordenarPor=sigla"
    all_parties = await fetch_data(parties_url)
    party_id = None
    for party in all_parties['dados']:
        if party['sigla'].upper() == party_initials.upper():
            party_id = party['id']
            break
    if not party_id:
        raise HTTPException(status_code=404, detail=f"Party with initials '{party_initials}' not found.")

    # 2. Get party members
    members_url = f"https://dadosabertos.camara.leg.br/api/v2/partidos/{party_id}/membros"
    members_data = await fetch_data(members_url)
    
    # 3. Get propositions from all members (this can be slow and data-intensive)
    text_for_wordcloud = ""
    deputy_ids = [member['id'] for member in members_data.get('dados', [])]

    # Limit the number of deputies to fetch propositions from to avoid long waits
    for dep_id in deputy_ids[:10]: # Fetching for first 10 deputies as a sample
        props_url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes?idDeputadoAutor={dep_id}&itens=100&ordem=DESC&ordenarPor=id"
        try:
            propositions_data = await fetch_data(props_url)
            text_for_wordcloud += ' '.join([prop['ementa'] for prop in propositions_data.get('dados', []) if prop.get('ementa')])
        except HTTPException as e:
            logging.warning(f"Could not fetch propositions for deputy {dep_id}: {e.detail}")
            continue # Continue to the next deputy

    wordcloud_path = os.path.join("cache_perfis", f"wordcloud_party_{party_initials}.png")
    generate_wordcloud(text_for_wordcloud, wordcloud_path)

    return {
        "sigla": party_initials,
        "id": party_id,
        "membros": deputy_ids,
        "wordcloud_url": f"/wordcloud/partido/{party_initials}.png"
    }


async def analyze_deputy_profile(deputy_id: int):
    """
    Gera uma análise de perfil para um deputado usando um modelo de linguagem, com foco em discursos.
    """
    logging.info(f"Starting discourse analysis for deputy {deputy_id}")

    # 1. Fetch deputy and speech data
    deputy_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputy_id}"
    
    # Fetch speeches from the last 2 years for a relevant sample
    data_fim = datetime.now().strftime('%Y-%m-%d')
    data_inicio = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    speeches = await get_deputy_speeches(deputy_id, data_inicio, data_fim)

    # If no speeches in the last 2 years, try from the beginning of the 56th legislature
    if not speeches:
        logging.info(f"No speeches found for deputy {deputy_id} in the last 2 years. Trying a wider date range.")
        data_inicio = "2019-02-01"
        speeches = await get_deputy_speeches(deputy_id, data_inicio, data_fim)

    try:
        deputy_data = await fetch_data(deputy_url)
    except HTTPException as e:
        raise e

    # 2. Consolidate data
    deputy_info = deputy_data.get("dados", {})
    speech_contents = [s.get('resumo') or s.get('transcricao') for s in speeches if s.get('resumo') or s.get('transcricao')]

    if not speech_contents:
        return {"analysis": "Análise não pôde ser gerada: Não foram encontrados discursos ou transcrições para este parlamentar no período analisado."}

    # Dinamicamente limita o número de discursos para evitar exceder o limite de tokens
    limited_speech_contents = []
    current_char_count = 0
    # Um limite seguro para o conteúdo dos discursos, para não estourar o limite de tokens do prompt
    CHAR_LIMIT = 28000  

    for speech in speech_contents:
        # Adiciona o tamanho do discurso atual ao contador
        current_char_count += len(speech)
        
        # Se o limite for excedido, para de adicionar discursos
        if current_char_count > CHAR_LIMIT:
            break
        
        # Adiciona o discurso à lista
        limited_speech_contents.append(speech)

    # 3. Prepare the prompt for the LLM
    prompt_text = f'''
    **Análise de Perfil e Discurso Parlamentar**

    **Instrução:** Você é um analista político experiente e imparcial, especializado em análise de discurso e dados legislativos do Brasil. Sua tarefa é criar uma análise crítica e baseada em dados sobre o(a) deputado(a) a seguir.

    **Deputado(a):** {deputy_info.get('nomeCivil', 'N/A')}
    **Partido:** {deputy_info.get('ultimoStatus', {}).get('siglaPartido', 'N/A')}
    **Estado:** {deputy_info.get('ultimoStatus', {}).get('siglaUf', 'N/A')}

    **Dados para Análise:**

    1.  **Trechos de Discursos (resumos ou transcrições):**
        {json.dumps(limited_speech_contents, indent=2, ensure_ascii=False)}

    **Estrutura da Análise (Siga este formato OBRIGATORIAMENTE):**

    1.  **Biografia:** (Gere uma pequena biografia de 2-3 linhas sobre o deputado, mencionando seu nome, partido e estado de representação.)

    2.  **Análise de Tópicos (Top 5):** (Com base nos resumos/transcrições dos discursos fornecidos, identifique e liste os 5 temas mais recorrentes na fala do parlamentar. Apresente como um ranking.)

    3.  **Análise de Tom e Sentimento:** (Seja crítico e isento. Analise o tom geral dos discursos. O parlamentar adota uma postura mais conciliadora ou de oposição? Use trechos curtos dos resumos/transcrições dos discursos para exemplificar e provar seu ponto. Por exemplo: 'Ao discutir o tema X, o deputado afirmou: "[trecho do resumo/transcrição]", o que demonstra uma postura Y.')

    4.  **Nível de Toxicidade (0 a 100):** (Com base na linguagem usada nos resumos/transcrições, atribua uma pontuação de 0 a 100, onde 0 é "totalmente neutro e respeitoso" e 100 é "extremamente tóxico e desrespeitoso". Justifique a pontuação com base em exemplos.)

    **Importante:**
    - **Seja Crítico e Isento:** A análise deve ser crítica, mas não elogiosa demais. Evite opiniões pessoais e viés ideologia.
    - **Base em Dados:** Fundamente TODA a sua análise nos resumos/transcrições de discursos fornecidos. Não invente informações.
    - **Use Exemplos:** É obrigatório o uso de trechos dos resumos/transcrições para justificar a análise de tom e a pontuação de toxicidade.
    '''

    # 4. Call the LLM
    if not GROQ_API_KEYS:
        raise HTTPException(status_code=500, detail="API keys for analysis service are not configured.")

    analysis_content = "Análise não pôde ser gerada devido a um erro no serviço."
    max_retries = len(GROQ_API_KEYS)
    for attempt in range(max_retries):
        try:
            client = get_groq_client()
            logging.info(f"Attempt {attempt + 1}/{max_retries}: Calling Groq API with key index {current_key_index -1}")
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_text}],
                model="llama-3.3-70b-versatile",
            )
            analysis_content = chat_completion.choices[0].message.content
            logging.info(f"Successfully generated analysis for deputy {deputy_id}")
            break  # Success
        except Exception as e:
            logging.error(f"Groq API call failed on attempt {attempt + 1}: {e}")
            if "rate limit" in str(e).lower():
                logging.warning("Rate limit likely hit. Waiting for 60 seconds before retrying.")
                time.sleep(60)
            if attempt == max_retries - 1:
                raise HTTPException(status_code=503, detail="Analysis service is currently unavailable after multiple retries.")

    return {"analysis": analysis_content}