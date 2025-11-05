import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from services import (
    get_party_details_and_generate_wordcloud,
    get_toxicity_ranking,
    get_speech_ranking,
    get_party_speech_ranking
)
from utils import load_cache, save_cache
import logging

# Setup

app = FastAPI()

# Ensure cache directories exist
os.makedirs("cache_geral", exist_ok=True)
os.makedirs("cache_perfis", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/ranking/discursos/deputados")
async def ranking_discursos_deputados(ordem: str = Query('desc', enum=["asc", "desc"])):
    try:
        ranking = get_speech_ranking(ordem)
        return ranking
    except Exception as e:
        logging.error(f"Error in /ranking/discursos/deputados: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/ranking/discursos/partidos")
async def ranking_discursos_partidos():
    try:
        ranking = get_party_speech_ranking()
        return ranking
    except Exception as e:
        logging.error(f"Error in /ranking/discursos/partidos: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/ranking/toxicidade")
async def ranking_toxicidade():
    try:
        ranking = get_toxicity_ranking()
        return ranking
    except Exception as e:
        logging.error(f"Error in /ranking/toxicidade: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/deputado/{deputy_id}")
async def get_deputado_perfil(deputy_id: int):
    """
    Endpoint para obter detalhes de um deputado e gerar uma nuvem de palavras.
    Otimizado com cache.
    """
    cache_key = f"deputy_details_{deputy_id}"
    cached_data = load_cache(cache_key, "cache_perfis", expiration_minutes=1440) # 24 horas
    if cached_data:
        return cached_data

    try:
        data = await get_deputy_details_and_generate_wordcloud(deputy_id)
        save_cache(cache_key, data, "cache_perfis")
        return data
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error getting deputy profile for {deputy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deputy details.")


@app.get("/partido/{party_initials}")
async def get_partido_perfil(party_initials: str):
    """
    Endpoint para obter detalhes de um partido e gerar uma nuvem de palavras.
    Otimizado com cache.
    """
    cache_key = f"party_details_{party_initials}"
    cached_data = load_cache(cache_key, "cache_perfis", expiration_minutes=1440) # 24 horas
    if cached_data:
        return cached_data

    try:
        data = await get_party_details_and_generate_wordcloud(party_initials)
        save_cache(cache_key, data, "cache_perfis")
        return data
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error getting party profile for {party_initials}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve party details.")


@app.get("/analise/{deputy_id}")
async def get_analise_perfil(deputy_id: int):
    """
    Endpoint para gerar e retornar a análise de perfil de um deputado.
    Otimizado com cache.
    """
    cache_key = f"analise_{deputy_id}"
    cached_data = load_cache(cache_key, "cache_perfis", expiration_minutes=10080) # 7 dias
    if cached_data:
        return cached_data

    try:
        analysis = await analyze_deputy_profile(deputy_id)
        save_cache(cache_key, analysis, "cache_perfis")
        return analysis
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error in analysis for deputy {deputy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wordcloud/deputado/{deputy_id}.png")
async def get_wordcloud_deputado_imagem(deputy_id: int):
    """
    Retorna a imagem da nuvem de palavras de um deputado.
    """
    image_path = os.path.join("cache_perfis", f"wordcloud_{deputy_id}.png")
    if not os.path.exists(image_path):
        # Se a imagem não existe, tente gerá-la primeiro
        try:
            await get_deputy_details_and_generate_wordcloud(deputy_id)
        except HTTPException as e:
            # Se a geração falhar, retorne o erro apropriado
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except Exception as e:
            logging.error(f"Failed to generate wordcloud on the fly for deputy {deputy_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not generate or find the word cloud image.")

    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png")
    else:
        # Mesmo após a tentativa de geração, se o arquivo não existir, retorne 404
        raise HTTPException(status_code=404, detail="Word cloud image not found.")


@app.get("/wordcloud/partido/{party_initials}.png")
async def get_wordcloud_partido_imagem(party_initials: str):
    """
    Retorna a imagem da nuvem de palavras de um partido.
    """
    image_path = os.path.join("cache_perfis", f"wordcloud_party_{party_initials}.png")
    if not os.path.exists(image_path):
        try:
            await get_party_details_and_generate_wordcloud(party_initials)
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except Exception as e:
            logging.error(f"Failed to generate wordcloud on the fly for party {party_initials}: {e}")
            raise HTTPException(status_code=500, detail="Could not generate or find the word cloud image.")

    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Word cloud image not found.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)