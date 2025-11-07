import os
import shutil

import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import HTTPException

# Garante que o app do FastAPI seja importado corretamente
from main import app

# ID de um deputado real para testes de integração (ex: Abilio Brunini - 220574)
# Usar um ID fixo ajuda a ter testes mais consistentes.
DEPUTY_ID_FOR_TEST = 220574
BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(autouse=True)
def clear_cache_and_mock_load_cache(mocker):
    if os.path.exists("cache_perfis"):
        shutil.rmtree("cache_perfis")
    mocker.patch('main.load_cache', return_value=None)

@pytest_asyncio.fixture
async def client():
    """Cria um cliente HTTP assíncrono para os testes."""
    async with AsyncClient(base_url=BASE_URL, timeout=60) as async_client:
        yield async_client

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Testa o endpoint raiz ("/")."""
    response = await client.get("/")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "API Voz do Plenário"
    # Corrigido: Verifica a chave descritiva, não a URL
    assert "analise_deputado" in json_response["endpoints"]

@pytest.mark.asyncio
async def test_get_deputy_wordcloud_returns_png(client: AsyncClient):
    """
    Testa se o endpoint de wordcloud retorna uma imagem PNG com sucesso.
    Este é um teste de integração, pois faz uma chamada real à API da Câmara.
    """
    response = await client.get(f"/wordcloud/deputado/{DEPUTY_ID_FOR_TEST}.png")
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/png'
    assert len(response.content) > 100

@pytest.mark.asyncio
async def test_analyze_deputy_speeches_mocked(client: AsyncClient, mocker):
    """
    Testa o endpoint de análise com a chamada ao serviço Groq mockada.
    """
    mocked_analysis_result = {"analysis": "Esta é uma análise mockada pela IA."}
    mocker.patch('main.analyze_deputy_profile', return_value=mocked_analysis_result)

    response = await client.get(f"/analise/{DEPUTY_ID_FOR_TEST}")

    assert response.status_code == 200
    assert response.json() == mocked_analysis_result

@pytest.mark.asyncio
async def test_analyze_speeches_no_api_key(client: AsyncClient, mocker):
    """
    Testa se o endpoint de análise falha corretamente (status 400) sem chave de API.
    """
    mocker.patch('services.GROQ_API_KEYS', [])

    response = await client.get(f"/analise/{DEPUTY_ID_FOR_TEST}")

    assert response.status_code == 503
    json_response = response.json()
    assert "Analysis service is currently unavailable after multiple retries." in json_response["detail"]

@pytest.mark.asyncio
async def test_wordcloud_no_speeches_found(client: AsyncClient, mocker):
    """
    Testa se o endpoint de wordcloud retorna um erro 404 quando nenhum discurso é encontrado.
    """
    mocker.patch('main.get_deputy_details_and_generate_wordcloud', side_effect=HTTPException(status_code=404, detail="Deputy not found."))

    response = await client.get(f"/wordcloud/deputado/0.png")

    assert response.status_code == 404
    assert "Deputy not found." in response.json()["detail"]