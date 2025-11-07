import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from services import (
    get_all_deputies,
    get_deputy_details_and_generate_wordcloud,
    get_deputy_speeches,
    get_deputies_by_party,
    get_speeches_by_party,
    get_party_details_and_generate_wordcloud,
    analyze_deputy_profile, # Added
)
import logging
from datetime import datetime, timedelta

# Setup
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Ensure cache directories exist
os.makedirs("cache_perfis", exist_ok=True)

@app.get("/")
async def root():
    return {"message": "API da Câmara dos Deputados"}

@app.get("/deputados")
async def list_deputados():
    deputados = await get_all_deputies()
    return {"total": len(deputados), "deputados": deputados}

@app.get("/deputados/{deputy_id}")
async def get_deputado(deputy_id: int):
    try:
        return await get_deputy_details_and_generate_wordcloud(deputy_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error getting deputy details for {deputy_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/deputados/{deputy_id}/discursos")
async def get_discursos_deputado(
    deputy_id: int,
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
):
    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now().strftime('%Y-%m-%d')
    
    speeches = await get_deputy_speeches(deputy_id, data_inicio, data_fim)
    return {"total_discursos": len(speeches), "discursos": speeches}

@app.get("/deputados/{deputy_id}/wordcloud")
async def get_wordcloud_deputado(deputy_id: int):
    image_path = os.path.join("cache_perfis", f"wordcloud_{deputy_id}.png")
    if not os.path.exists(image_path):
        try:
            await get_deputy_details_and_generate_wordcloud(deputy_id)
        except HTTPException as e:
            raise e
    
    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Wordcloud not found.")

@app.get("/partidos/{sigla}/deputados")
async def get_deputados_partido(sigla: str):
    deputados = await get_deputies_by_party(sigla)
    return {"partido": sigla, "total_deputados": len(deputados), "deputados": deputados}

@app.get("/partidos/{sigla}/discursos")
async def get_discursos_partido(
    sigla: str,
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
):
    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now().strftime('%Y-%m-%d')

    speeches = await get_speeches_by_party(sigla, data_inicio, data_fim)
    return {"partido": sigla, "total_discursos": len(speeches), "discursos": speeches}

@app.get("/partidos/{sigla}/wordcloud")
async def get_wordcloud_partido(sigla: str):
    image_path = os.path.join("cache_perfis", f"wordcloud_party_{sigla}.png")
    if not os.path.exists(image_path):
        try:
            await get_party_details_and_generate_wordcloud(sigla)
        except HTTPException as e:
            raise e

    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Wordcloud not found.")

@app.get("/analise/{deputy_id}")
async def get_analise_perfil(deputy_id: int):
    """
    Endpoint para gerar e retornar a análise de perfil de um deputado.
    """
    try:
        analysis = await analyze_deputy_profile(deputy_id)
        return analysis
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error in analysis for deputy {deputy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
