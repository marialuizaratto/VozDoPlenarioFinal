import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"


def test_ranking_toxicidade():
    """Tests the toxicity ranking endpoint."""
    try:
        response = httpx.get(f"{BASE_URL}/ranking/toxicidade", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 1:
            assert data[0].get("toxicity_score", 0) >= data[1].get("toxicity_score", 0)
        print("✅ Teste /ranking/toxicidade passou.")
    except Exception as e:
        pytest.fail(f"Teste /ranking/toxicidade falhou: {e}")

def test_ranking_discursos_deputados_desc():
    """Tests the descending speech ranking endpoint for deputies."""
    try:
        response = httpx.get(f"{BASE_URL}/ranking/discursos/deputados?ordem=desc", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 1:
            assert data[0].get("speech_count", 0) >= data[1].get("speech_count", 0)
        print("✅ Teste /ranking/discursos/deputados?ordem=desc passou.")
    except Exception as e:
        pytest.fail(f"Teste /ranking/discursos/deputados?ordem=desc falhou: {e}")

def test_ranking_discursos_deputados_asc():
    """Tests the ascending speech ranking endpoint for deputies."""
    try:
        response = httpx.get(f"{BASE_URL}/ranking/discursos/deputados?ordem=asc", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 1:
            assert data[0].get("speech_count", 0) <= data[1].get("speech_count", 0)
        print("✅ Teste /ranking/discursos/deputados?ordem=asc passou.")
    except Exception as e:
        pytest.fail(f"Teste /ranking/discursos/deputados?ordem=asc falhou: {e}")

def test_ranking_discursos_partidos():
    """Tests the speech ranking endpoint for parties."""
    try:
        response = httpx.get(f"{BASE_URL}/ranking/discursos/partidos", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 1:
            assert data[0].get("mediaDiscursosPorDeputado", 0) >= data[1].get("mediaDiscursosPorDeputado", 0)
        print("✅ Teste /ranking/discursos/partidos passou.")
    except Exception as e:
        pytest.fail(f"Teste /ranking/discursos/partidos falhou: {e}")
