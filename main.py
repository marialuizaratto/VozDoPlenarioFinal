import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from services import (
    get_all_deputies,
    get_deputy_details_and_generate_wordcloud,
    get_deputy_speeches,
    get_deputies_by_party,
    get_speeches_by_party,
    get_party_details_and_generate_wordcloud,
    get_deputy_ranking,
    get_party_activity_ranking,
    analyze_deputy_profile,
)
import logging
from datetime import datetime, timedelta

# Setup
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Permite que o front-end (Vercel) acesse esta API de outro domínio.
# Liberado para qualquer origem (*) por enquanto para não travar o site;
# se quiser restringir depois, troque "*" pela URL exata do seu site no Vercel.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure cache directories exist
os.makedirs("cache_perfis", exist_ok=True)
os.makedirs("csv_data", exist_ok=True)

@app.get("/debug/groq")
def debug_groq():
    """
    Endpoint temporário de diagnóstico para testar a conexão com a Groq.
    Não expõe as chaves completas. REMOVER depois de resolver o problema.
    """
    import httpx as _httpx
    keys = {
        "GROQ_API_KEY_1": os.environ.get("GROQ_API_KEY_1"),
        "GROQ_API_KEY_2": os.environ.get("GROQ_API_KEY_2"),
        "GROQ_API_KEY_3": os.environ.get("GROQ_API_KEY_3"),
    }

    resultado = {}
    for nome, valor in keys.items():
        if not valor:
            resultado[nome] = {"presente": False}
            continue

        info = {"presente": True, "prefixo": valor[:8]}

        # Testa endpoint de modelos (mais simples, confirma conectividade + autenticação)
        try:
            with _httpx.Client(timeout=15.0) as client:
                r = client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {valor}"},
                )
                info["teste_models_status"] = r.status_code
                info["teste_models_corpo"] = r.text[:300]
        except Exception as e:
            info["teste_models_erro"] = str(e)

        # Testa o endpoint de chat completions de verdade
        try:
            with _httpx.Client(timeout=15.0) as client:
                r = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {valor}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": "diga oi"}],
                    },
                )
                info["teste_chat_status"] = r.status_code
                info["teste_chat_corpo"] = r.text[:300]
        except Exception as e:
            info["teste_chat_erro"] = str(e)

        resultado[nome] = info

    return resultado


@app.get("/")
def root():
    return {"message": "API da Câmara dos Deputados - CSV Cache Mode"}

@app.get("/deputados")
def list_deputados():
    deputados = get_all_deputies()
    return {"total": len(deputados), "deputados": deputados}

@app.get("/deputados/{deputy_id}")
def get_deputado(deputy_id: int):
    try:
        return get_deputy_details_and_generate_wordcloud(deputy_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error getting deputy details for {deputy_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/deputados/{deputy_id}/discursos")
def get_discursos_deputado(
    deputy_id: int,
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
):
    speeches = get_deputy_speeches(deputy_id, data_inicio, data_fim)
    response = {"total_discursos": len(speeches), "discursos": speeches}
    if not speeches:
        response["mensagem"] = "Este(a) deputado(a) não possui discursos registrados no período analisado."
    return response

@app.get("/deputados/{deputy_id}/wordcloud")
def get_wordcloud_deputado(deputy_id: int):
    image_path = os.path.join("cache_perfis", f"wordcloud_{deputy_id}.png")
    # Always generate a fresh one based on CSV data
    try:
        get_deputy_details_and_generate_wordcloud(deputy_id)
    except HTTPException as e:
        raise e

    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Wordcloud could not be generated.")

@app.get("/deputados/{deputy_id}/analise")
@app.get("/analise/{deputy_id}")
def get_analise_deputado(deputy_id: int):
    """
    Retorna uma análise de IA (via Groq) sobre os discursos recentes do deputado.
    Disponível em duas rotas (/deputados/{id}/analise e /analise/{id}) para
    compatibilidade com o front-end.
    """
    try:
        return analyze_deputy_profile(deputy_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Erro ao gerar análise de IA para o deputado {deputy_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar análise.")

@app.get("/partidos/{sigla}/deputados")
def get_deputados_partido(sigla: str):
    deputados = get_deputies_by_party(sigla)
    return {"partido": sigla, "total_deputados": len(deputados), "deputados": deputados}

@app.get("/partidos/{sigla}/discursos")
def get_discursos_partido(
    sigla: str,
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
):
    speeches = get_speeches_by_party(sigla, data_inicio, data_fim)
    response = {"partido": sigla, "total_discursos": len(speeches), "discursos": speeches}
    if not speeches:
        response["mensagem"] = "Nenhum discurso registrado para este partido no período analisado."
    return response

@app.get("/partidos/{sigla}/wordcloud")
def get_wordcloud_partido(sigla: str):
    image_path = os.path.join("cache_perfis", f"wordcloud_party_{sigla}.png")
    # Always generate a fresh one based on CSV data
    try:
        get_party_details_and_generate_wordcloud(sigla)
    except HTTPException as e:
        raise e

    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Wordcloud could not be generated.")


# --- Ranking Endpoints ---

@app.get("/ranking/deputados/mais-falam")
def get_ranking_deputados_mais_falam():
    """
    Retorna um ranking dos 50 deputados que mais fizeram discursos.
    """
    try:
        return get_deputy_ranking(order='most')
    except Exception as e:
        logging.error(f"Erro ao gerar ranking de deputados que mais falam: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar ranking.")

@app.get("/ranking/deputados/menos-falam")
def get_ranking_deputados_menos_falam():
    """
    Retorna um ranking dos 50 deputados que menos fizeram discursos.
    """
    try:
        return get_deputy_ranking(order='least')
    except Exception as e:
        logging.error(f"Erro ao gerar ranking de deputados que menos falam: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar ranking.")

@app.get("/ranking/partidos/mais-ativos")
def get_ranking_partidos_mais_ativos():
    """
    Retorna um ranking de partidos por atividade proporcional (média de discursos por deputado).
    """
    try:
        return get_party_activity_ranking()
    except Exception as e:
        logging.error(f"Erro ao gerar ranking de partidos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar ranking.")


# Main execution for local development
if __name__ == "__main__":
    import uvicorn
    # Use the standard port 8000 for local dev
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
