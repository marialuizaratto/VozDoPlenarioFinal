
import pytest
import pytest_asyncio
from httpx import AsyncClient
import httpx
from main import app

# ID de um deputado real para o teste de integração
DEPUTY_ID_FOR_TEST = 220574 

@pytest_asyncio.fixture
async def client():
    """Cria um cliente HTTP assíncrono para os testes com timeout estendido."""
    timeout = httpx.Timeout(60.0)  # 60 segundos de timeout
    async with AsyncClient(app=app, base_url="http://test", timeout=timeout) as async_client:
        yield async_client

@pytest.mark.asyncio
async def test_analyze_deputy_speeches_integration(client: AsyncClient):
    """
    Testa o endpoint de análise de discursos com uma chamada real à API Groq.
    Este teste depende de uma chave de API válida no arquivo .env.
    """
    params = {
        "data_inicio": "2024-01-01",
        "data_fim": "2024-03-31"
    }
    
    response = await client.get(f"/analise/{DEPUTY_ID_FOR_TEST}", params=params)
    
    assert response.status_code == 200
    
    json_response = response.json()
    
    # Verifica se a resposta contém a chave 'analysis' e se não está vazia
    assert "analysis" in json_response
    assert isinstance(json_response["analysis"], str)
    assert len(json_response["analysis"]) > 20  # Espera-se uma análise com algum conteúdo

    # Opcional: Imprime a análise para verificação manual durante o teste
    print(f"Análise da IA: {json_response['analysis']}")
