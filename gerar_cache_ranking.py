import asyncio
import os
from services import get_all_deputies, analyze_deputy_profile
from utils import save_cache

CACHE_DIR = "cache_perfis"

async def gerar_cache_analises():
    """
    Busca todos os deputados, gera a análise de perfil para cada um usando a IA
    e salva o resultado em arquivos de cache individuais.
    """
    print("--- INICIANDO GERAÇÃO DE CACHE DE ANÁLISES DE PERFIL ---")
    os.makedirs(CACHE_DIR, exist_ok=True)

    all_deputies = await get_all_deputies()
    if not all_deputies:
        print("ERRO: Não foi possível buscar a lista de deputados.")
        return

    # Limita a 5 execuções simultâneas para não sobrecarregar a API do Groq
    porteiro = asyncio.Semaphore(5)

    async def gerar_analise(deputy):
        async with porteiro:
            dep_id = deputy.get('id')
            cache_key = f"analise_{dep_id}"
            
            # Verifica se a análise já existe no cache
            # NOTA: A função load_cache não está implementada neste fluxo,
            # então a verificação de existência de arquivo é feita manualmente.
            cache_file_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
            if os.path.exists(cache_file_path):
                print(f"Análise para {deputy.get('nome')} ({dep_id}) já existe. Pulando.")
                return

            try:
                print(f"Gerando análise para: {deputy.get('nome')} ({dep_id})")
                analysis = await analyze_deputy_profile(dep_id)
                save_cache(cache_key, analysis, CACHE_DIR)
                print(f"Análise para {dep_id} salva com sucesso.")
            except Exception as e:
                print(f"ERRO ao gerar análise para o dep {dep_id}: {e}")

    tasks = [gerar_analise(dep) for dep in all_deputies]
    await asyncio.gather(*tasks)

    print("\n--- GERAÇÃO DE CACHE DE ANÁLISES CONCLUÍDA COM SUCESSO! ---")

if __name__ == "__main__":
    asyncio.run(gerar_cache_analises())