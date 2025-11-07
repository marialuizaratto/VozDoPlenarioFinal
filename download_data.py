
import httpx
import csv
import os
import time
from datetime import datetime, timedelta

# --- Configuration ---
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
}
TIMEOUT_CONFIG = httpx.Timeout(30.0, connect=20.0)
DATA_DIR = "csv_data"

# --- Helper Functions ---

def ensure_data_dir():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def fetch_data_sync(url: str):
    """Synchronous data fetcher with retry logic for the download script."""
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT_CONFIG) as client:
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error for {url}: {e.response.status_code} - Retrying in 15s...")
            time.sleep(15)
            return fetch_data_sync(url) # Retry
        except Exception as e:
            print(f"An unexpected error occurred for {url}: {e} - Retrying in 15s...")
            time.sleep(15)
            return fetch_data_sync(url) # Retry

# --- Download Functions ---

def download_deputies():
    """Downloads all deputies and saves them to deputados.csv."""
    print("Starting download of all deputies...")
    filepath = os.path.join(DATA_DIR, "deputados.csv")
    
    url = f"{BASE_URL}/deputados?ordem=ASC&ordenarPor=nome"
    all_deputies = []
    page = 1
    while True:
        paginated_url = f"{url}&pagina={page}&itens=100"
        print(f"Fetching deputies page {page}...")
        response = fetch_data_sync(paginated_url)
        deputies = response.get("dados", [])
        if not deputies:
            break
        all_deputies.extend(deputies)
        page += 1
        time.sleep(1) # Be respectful to the API

    if not all_deputies:
        print("No deputies found. Aborting.")
        return

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        fieldnames = all_deputies[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_deputies)
        
    print(f"Finished: {len(all_deputies)} deputies saved to {filepath}")
    return all_deputies

def download_speeches(deputies: list):
    """Downloads all speeches for a given list of deputies from the last 90 days."""
    print("\nStarting download of speeches from the last 90 days...")
    filepath = os.path.join(DATA_DIR, "discursos.csv")
    
    # Overwrite the file each time to create a fresh 90-day cache
    if os.path.exists(filepath):
        os.remove(filepath)

    fieldnames = None
    total_speeches_downloaded = 0
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        for i, deputy in enumerate(deputies):
            deputy_id = deputy['id']
            print(f"Downloading speeches for deputy {i+1}/{len(deputies)} (ID: {deputy_id})...")
            
            # Fetch speeches from the last 90 days
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            url = f"{BASE_URL}/deputados/{deputy_id}/discursos?dataInicio={start_date}&dataFim={end_date}&ordenarPor=dataHoraInicio&ordem=ASC"
            page = 1
            deputy_speeches = []
            while True:
                paginated_url = f"{url}&pagina={page}&itens=100"
                response = fetch_data_sync(paginated_url)
                speeches = response.get("dados", [])
                if not speeches:
                    break
                
                for speech in speeches:
                    speech['idDeputado'] = deputy_id
                
                deputy_speeches.extend(speeches)
                page += 1
                time.sleep(1)

            if not deputy_speeches:
                continue

            if fieldnames is None:
                # Use a comprehensive list of potential fields to handle missing keys
                fieldnames = ['idDeputado', 'dataHoraInicio', 'dataHoraFim', 'tipoDiscurso', 'keywords', 'sumario', 'transcricao', 'urlAudio', 'urlVideo', 'urlTexto']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
            else:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')

            writer.writerows(deputy_speeches)
            total_speeches_downloaded += len(deputy_speeches)
            print(f"  -> Found and saved {len(deputy_speeches)} speeches for deputy {deputy_id}.")

    print(f"\nFinished: A total of {total_speeches_downloaded} speeches saved to {filepath}")


# --- Main Execution ---

if __name__ == "__main__":
    ensure_data_dir()
    
    print("--- Voz do Plenário: Downloader de Dados ---")
    print("This script will download deputy and speech data from the last 90 days.")
    
    deputies_list = download_deputies()
    
    if deputies_list:
        download_speeches(deputies_list)
    
    print("\n--- Download complete! ---")
    print(f"Data saved in the '{DATA_DIR}' directory.")
