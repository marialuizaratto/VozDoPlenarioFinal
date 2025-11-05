"""
Testes para a API Voz do Plenário

Executar com: pytest
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient

# Garante que o app do FastAPI seja importado corretamente
from main import app

# ID de um deputado real para testes de integração (ex: Abilio Brunini - 220574)
# Usar um ID fixo ajuda a ter testes mais consistentes.
DEPUTY_ID_FOR_TEST = 220574

@pytest_asyncio.fixture
async def client():
    """Cria um cliente HTTP assíncrono para os testes."""
    async with AsyncClient(app=app, base_url="http://test") as async_client:
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
    params = {
        "data_inicio": "2024-01-01",
        "data_fim": "2024-03-31"
    }
    response = await client.get(f"/deputados/{DEPUTY_ID_FOR_TEST}/wordcloud", params=params)
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/png'
    assert len(response.content) > 100

@pytest.mark.asyncio
async def test_analyze_deputy_speeches_mocked(client: AsyncClient, mocker):
    """
    Testa o endpoint de análise com a chamada ao serviço Groq mockada.
    """
    mocked_analysis_result = "Esta é uma análise mockada pela IA."
    # Corrigido: Mock no local onde a função é usada (no módulo 'main')
    mocker.patch('main.analyze_speeches_with_groq', return_value=mocked_analysis_result)
    mocker.patch('main.get_deputy_by_id', return_value={"id": DEPUTY_ID_FOR_TEST, "nomeCivil": "Deputado Teste"})
    mocker.patch('main.get_deputy_speeches', return_value=[{"transcricao": "Discurso de teste."}])

    response = await client.get(f"/deputados/{DEPUTY_ID_FOR_TEST}/analise")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["analise"] == mocked_analysis_result

@pytest.mark.asyncio
async def test_analyze_speeches_no_api_key(client: AsyncClient, mocker):
    """
    Testa se o endpoint de análise falha corretamente (status 400) sem chave de API.
    """
    # Corrigido: Mock no local onde a função é usada (no módulo 'main')
    # A exceção de ValueError é levantada de dentro do serviço original
    mocker.patch('main.get_deputy_by_id', return_value={"id": DEPUTY_ID_FOR_TEST, "nomeCivil": "Deputado Teste"})
    mocker.patch('main.get_deputy_speeches', return_value=[{"transcricao": "Discurso de teste."}])
    # O mock abaixo garante que a função real (com a verificação da chave) seja chamada
    mocker.patch('services.GROQ_API_KEY', None)

    # Corrigido: Erro de digitação no nome da variável
    response = await client.get(f"/deputados/{DEPUTY_ID_FOR_TEST}/analise")

    assert response.status_code == 400
    json_response = response.json()
    assert "A chave da API do Groq não foi configurada" in json_response["detail"]

@pytest.mark.asyncio
async def test_wordcloud_no_speeches_found(client: AsyncClient, mocker):
    """
    Testa se o endpoint de wordcloud retorna um erro 404 quando nenhum discurso é encontrado.
    """
    # Corrigido: Mock no local onde a função é usada (no módulo 'main')
    mocker.patch('main.get_deputy_speeches', return_value=[])

    response = await client.get(f"/deputados/{DEPUTY_ID_FOR_TEST}/wordcloud")

    assert response.status_code == 404
    assert "Nenhum discurso encontrado" in response.json()["detail"]