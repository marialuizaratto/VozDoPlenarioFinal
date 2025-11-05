import asyncio
import json
import os
from datetime import datetime, timedelta

from services import get_all_deputies, get_deputy_speeches

CACHE_DIR = "cache_geral"
CACHE_FILE = os.path.join(CACHE_DIR, "discursos_deputados.json")

async def gerar_cache_discursos():
    """Busca todos os deputados, conta seus discursos e salva o resultado em um arquivo JSON."""
    print("--- INICIANDO GERAÇÃO DE CACHE DE CONTAGEM DE DISCURSOS ---")
    os.makedirs(CACHE_DIR, exist_ok=True)

    all_deputies = await get_all_deputies()
    if not all_deputies:
        print("ERRO: Não foi possível buscar a lista de deputados.")
        return

    porteiro = asyncio.Semaphore(20)
    data_fim = datetime.now().strftime('%Y-%m-%d')
    data_inicio = (datetime.now() - timedelta(days=365*4)).strftime('%Y-%m-%d') # Approx. 4 years

    async def get_speech_count(deputy):
        async with porteiro:
            try:
                dep_id = deputy.get('id')
                print(f"Contando discursos de: {deputy.get('nome')} ({dep_id})")
                speeches = await get_deputy_speeches(dep_id, data_inicio, data_fim)
                deputy['speech_count'] = len(speeches)
                return deputy
            except Exception as e:
                print(f"ERRO ao contar discursos do dep {deputy.get('id')}: {e}")
                deputy['speech_count'] = 0
                return deputy

    tasks = [get_speech_count(dep) for dep in all_deputies]
    deputies_with_counts = await asyncio.gather(*tasks)

    print(f"\nSalvando contagem de discursos de {len(deputies_with_counts)} deputados em {CACHE_FILE}...")
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(deputies_with_counts, f, ensure_ascii=False, indent=4)
    
    print("--- GERAÇÃO DE CACHE DE DISCURSOS CONCLUÍDA COM SUCESSO! ---")

if __name__ == "__main__":
    asyncio.run(gerar_cache_discursos())
