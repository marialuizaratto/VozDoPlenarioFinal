
import httpx
import csv
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- Configuration ---
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
}
TIMEOUT_CONFIG = httpx.Timeout(30.0, connect=20.0)
DATA_DIR = "csv_data"
SLEEP_BETWEEN_REQUESTS = 0.5
MAX_WORKERS = 2

SPEECH_FIELDNAMES = [
    'idDeputado', 'dataHoraInicio', 'dataHoraFim', 'tipoDiscurso',
    'keywords', 'sumario', 'transcricao', 'urlAudio', 'urlVideo', 'urlTexto'
]

# --- Helper Functions ---

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def fetch_data_sync(url: str):
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT_CONFIG) as client:
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"\nHTTP Error for {url}: {e.response.status_code} - Retrying in 15s...")
            time.sleep(15)
            return fetch_data_sync(url)
        except Exception as e:
            print(f"\nError for {url}: {e} - Retrying in 15s...")
            time.sleep(15)
            return fetch_data_sync(url)

# --- Download Functions ---

def download_deputies():
    print("Baixando lista de deputados...")
    filepath = os.path.join(DATA_DIR, "deputados.csv")

    url = f"{BASE_URL}/deputados?ordem=ASC&ordenarPor=nome"
    all_deputies = []
    page = 1
    with tqdm(desc="Páginas de deputados", unit="pág") as pbar:
        while True:
            paginated_url = f"{url}&pagina={page}&itens=100"
            response = fetch_data_sync(paginated_url)
            deputies = response.get("dados", [])
            if not deputies:
                break
            all_deputies.extend(deputies)
            pbar.update(1)
            page += 1
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    if not all_deputies:
        print("Nenhum deputado encontrado.")
        return []

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        fieldnames = all_deputies[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_deputies)

    print(f"{len(all_deputies)} deputados salvos em {filepath}")
    return all_deputies


def _fetch_speeches_for_deputy(deputy: dict) -> list:
    """Busca todos os discursos de um deputado (última janela de 90 dias). Thread-safe."""
    deputy_id = deputy['id']
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    url = (
        f"{BASE_URL}/deputados/{deputy_id}/discursos"
        f"?dataInicio={start_date}&dataFim={end_date}"
        f"&ordenarPor=dataHoraInicio&ordem=ASC"
    )

    speeches = []
    page = 1
    while True:
        response = fetch_data_sync(f"{url}&pagina={page}&itens=100")
        page_data = response.get("dados", [])
        if not page_data:
            break
        for speech in page_data:
            speech['idDeputado'] = deputy_id
        speeches.extend(page_data)
        page += 1
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    return speeches


def download_speeches(deputies: list):
    print(f"\nBaixando discursos dos últimos 90 dias ({len(deputies)} deputados, {MAX_WORKERS} simultâneos)...")
    filepath = os.path.join(DATA_DIR, "discursos.csv")

    all_speeches = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_speeches_for_deputy, dep): dep for dep in deputies}
        with tqdm(total=len(deputies), desc="Deputados", unit="dep") as pbar:
            for future in as_completed(futures):
                dep = futures[future]
                try:
                    speeches = future.result()
                    all_speeches.extend(speeches)
                    pbar.set_postfix(dep=dep.get('nome', '')[:25], discursos=len(speeches))
                except Exception as e:
                    pbar.write(f"ERRO {dep.get('nome')}: {e}")
                finally:
                    pbar.update(1)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SPEECH_FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_speeches)

    print(f"\n{len(all_speeches)} discursos salvos em {filepath}")


# --- Main Execution ---

if __name__ == "__main__":
    ensure_data_dir()

    print("--- Voz do Plenário: Downloader de Dados ---")
    print(f"Sleep entre requisições: {SLEEP_BETWEEN_REQUESTS}s | Workers: {MAX_WORKERS}")

    deputies_list = download_deputies()

    if deputies_list:
        download_speeches(deputies_list)

    print("\n--- Download concluído! ---")
    print(f"Dados salvos em '{DATA_DIR}/'")
