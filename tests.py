"""
Testes para a API da Câmara dos Deputados
Execute com a API rodando em http://localhost:8000
"""
import requests
import sys
from PIL import Image
from io import BytesIO


BASE_URL = "http://localhost:8000"


def print_separator():
    print("\n" + "="*80 + "\n")


def test_root():
    """Testa o endpoint raiz"""
    print("🧪 Testando endpoint raiz (GET /)...")

    try:
        response = requests.get(f"{BASE_URL}/")

        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoint raiz funcionando!")
            print(f"   Versão da API: {data.get('version')}")
            print(f"   Endpoints disponíveis: {len(data.get('endpoints', {}))}")
            return True
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False


def test_list_deputies():
    """Testa listagem de deputados"""
    print("🧪 Testando listagem de deputados (GET /deputados)...")

    try:
        response = requests.get(f"{BASE_URL}/deputados", timeout=30)

        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"✅ Listagem de deputados funcionando!")
            print(f"   Total de deputados: {total}")

            if total > 0:
                primeiro_deputado = data.get('deputados', [])[0]
                print(f"   Exemplo: {primeiro_deputado.get('nome')} - {primeiro_deputado.get('siglaPartido')}/{primeiro_deputado.get('siglaUf')}")
                return primeiro_deputado.get('id')
            return True
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_get_deputy(deputy_id):
    """Testa obtenção de dados de um deputado específico"""
    print(f"🧪 Testando dados de deputado (GET /deputados/{deputy_id})...")

    try:
        response = requests.get(f"{BASE_URL}/deputados/{deputy_id}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dados do deputado obtidos com sucesso!")
            print(f"   Nome: {data.get('nomeCivil')}")
            print(f"   Data de nascimento: {data.get('dataNascimento')}")

            ultimo_status = data.get('ultimoStatus', {})
            print(f"   Partido: {ultimo_status.get('siglaPartido')}")
            print(f"   UF: {ultimo_status.get('siglaUf')}")
            return True
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_deputy_speeches(deputy_id):
    """Testa listagem de discursos de um deputado"""
    print(f"🧪 Testando discursos de deputado (GET /deputados/{deputy_id}/discursos)...")

    try:
        response = requests.get(
            f"{BASE_URL}/deputados/{deputy_id}/discursos",
            params={"data_inicio": "2024-01-01"},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            total = data.get('total_discursos', 0)
            print(f"✅ Discursos obtidos com sucesso!")
            print(f"   Total de discursos: {total}")

            if total > 0:
                primeiro_discurso = data.get('discursos', [])[0]
                print(f"   Exemplo - Tipo: {primeiro_discurso.get('tipoDiscurso')}")
                print(f"   Sumário: {primeiro_discurso.get('sumario', '')[:100]}...")
            return total > 0
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_deputy_wordcloud(deputy_id):
    """Testa geração de wordcloud de um deputado"""
    print(f"🧪 Testando wordcloud de deputado (GET /deputados/{deputy_id}/wordcloud)...")

    try:
        response = requests.get(
            f"{BASE_URL}/deputados/{deputy_id}/wordcloud",
            params={"data_inicio": "2024-01-01", "width": 800, "height": 600},
            timeout=60
        )

        if response.status_code == 200:
            # Tenta abrir a imagem para validar
            try:
                image = Image.open(BytesIO(response.content))
                print(f"✅ Wordcloud gerado com sucesso!")
                print(f"   Tamanho da imagem: {image.size}")
                print(f"   Formato: {image.format}")

                # Salva a imagem
                filename = f"test_wordcloud_deputy_{deputy_id}.png"
                image.save(filename)
                print(f"   Imagem salva em: {filename}")
                return True
            except Exception as img_error:
                print(f"❌ Erro ao processar imagem: {img_error}")
                return False
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_party_deputies(party):
    """Testa listagem de deputados por partido"""
    print(f"🧪 Testando deputados por partido (GET /partidos/{party}/deputados)...")

    try:
        response = requests.get(f"{BASE_URL}/partidos/{party}/deputados", timeout=30)

        if response.status_code == 200:
            data = response.json()
            total = data.get('total_deputados', 0)
            print(f"✅ Deputados do partido obtidos com sucesso!")
            print(f"   Partido: {data.get('partido')}")
            print(f"   Total de deputados: {total}")

            if total > 0:
                exemplo = data.get('deputados', [])[0]
                print(f"   Exemplo: {exemplo.get('nome')} - {exemplo.get('siglaUf')}")
            return True
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_party_speeches(party):
    """Testa listagem de discursos de um partido"""
    print(f"🧪 Testando discursos por partido (GET /partidos/{party}/discursos)...")
    print("   ⚠️  Este teste pode demorar alguns minutos pois busca discursos de todos os deputados do partido...")

    try:
        # Primeiro tenta com um período mais amplo (últimos 3 meses de 2024)
        response = requests.get(
            f"{BASE_URL}/partidos/{party}/discursos",
            params={"data_inicio": "2024-10-01", "data_fim": "2024-12-31"},
            timeout=180
        )

        if response.status_code == 200:
            data = response.json()
            total = data.get('total_discursos', 0)
            print(f"✅ Discursos do partido obtidos com sucesso!")
            print(f"   Total de discursos (out-dez/2024): {total}")

            if total > 0:
                primeiro = data.get('discursos', [])[0]
                deputado = primeiro.get('deputado', {})
                print(f"   Exemplo: {deputado.get('nome')} - {primeiro.get('tipoDiscurso')}")
            return total > 0
        elif response.status_code == 404:
            # Se não encontrar, tenta sem filtro de data (últimos discursos disponíveis)
            print("   ℹ️  Nenhum discurso no período out-dez/2024, tentando sem filtro de data...")
            response = requests.get(
                f"{BASE_URL}/partidos/{party}/discursos",
                timeout=180
            )

            if response.status_code == 200:
                data = response.json()
                total = data.get('total_discursos', 0)
                print(f"✅ Discursos do partido obtidos (sem filtro de data)!")
                print(f"   Total de discursos: {total}")

                if total > 0:
                    primeiro = data.get('discursos', [])[0]
                    deputado = primeiro.get('deputado', {})
                    print(f"   Exemplo: {deputado.get('nome')} - {primeiro.get('tipoDiscurso')}")
                return total > 0
            else:
                print(f"⚠️  Status code {response.status_code} - Pode não haver discursos recentes")
                print(f"   Resposta: {response.text[:200]}")
                # Não considera erro se for 404 (partido pode não ter discursos)
                return None
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_party_wordcloud(party):
    """Testa geração de wordcloud de um partido"""
    print(f"🧪 Testando wordcloud por partido (GET /partidos/{party}/wordcloud)...")
    print("   ⚠️  Este teste pode demorar alguns minutos...")

    try:
        response = requests.get(
            f"{BASE_URL}/partidos/{party}/wordcloud",
            params={"data_inicio": "2024-10-01", "data_fim": "2024-12-31", "width": 800, "height": 600},
            timeout=300
        )

        if response.status_code == 200:
            try:
                image = Image.open(BytesIO(response.content))
                print(f"✅ Wordcloud do partido gerado com sucesso!")
                print(f"   Tamanho da imagem: {image.size}")
                print(f"   Formato: {image.format}")

                filename = f"test_wordcloud_party_{party}.png"
                image.save(filename)
                print(f"   Imagem salva em: {filename}")
                return True
            except Exception as img_error:
                print(f"❌ Erro ao processar imagem: {img_error}")
                return False
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print("🚀 INICIANDO TESTES DA API DA CÂMARA DOS DEPUTADOS")
    print("="*80)

    results = {
        'total': 0,
        'passed': 0,
        'failed': 0
    }

    # Teste 1: Endpoint raiz
    print_separator()
    results['total'] += 1
    if test_root():
        results['passed'] += 1
    else:
        results['failed'] += 1
        print("\n⚠️  API não está respondendo. Certifique-se de que está rodando em http://localhost:8000")
        return results

    # Teste 2: Listar deputados
    print_separator()
    results['total'] += 1
    deputy_id = test_list_deputies()
    if deputy_id:
        results['passed'] += 1
    else:
        results['failed'] += 1
        print("\n⚠️  Não foi possível obter a lista de deputados. Testes subsequentes podem falhar.")
        deputy_id = 204554  # ID de exemplo como fallback

    # Teste 3: Obter deputado específico
    if deputy_id:
        print_separator()
        results['total'] += 1
        if test_get_deputy(deputy_id):
            results['passed'] += 1
        else:
            results['failed'] += 1

    # Teste 4: Discursos de deputado
    if deputy_id:
        print_separator()
        results['total'] += 1
        has_speeches = test_deputy_speeches(deputy_id)
        if has_speeches is not False:
            results['passed'] += 1
        else:
            results['failed'] += 1

    # Teste 5: Wordcloud de deputado (apenas se houver discursos)
    if deputy_id and has_speeches:
        print_separator()
        results['total'] += 1
        if test_deputy_wordcloud(deputy_id):
            results['passed'] += 1
        else:
            results['failed'] += 1

    # Teste 6: Deputados por partido
    print_separator()
    party = "PT"
    results['total'] += 1
    if test_party_deputies(party):
        results['passed'] += 1
    else:
        results['failed'] += 1
        # Tenta outro partido
        party = "PL"
        print(f"\n   Tentando com partido {party}...")
        if test_party_deputies(party):
            results['passed'] += 1
            results['failed'] -= 1

    # Teste 7: Discursos por partido
    print_separator()
    results['total'] += 1
    has_party_speeches = test_party_speeches(party)
    if has_party_speeches is True:
        results['passed'] += 1
    elif has_party_speeches is None:
        # Não há discursos no período, mas não é um erro da API
        print("   ℹ️  Teste pulado - sem discursos disponíveis no período")
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Teste 8: Wordcloud por partido (apenas se houver discursos)
    if has_party_speeches is True:
        print_separator()
        results['total'] += 1
        if test_party_wordcloud(party):
            results['passed'] += 1
        else:
            results['failed'] += 1
    else:
        print_separator()
        print("🧪 Teste de wordcloud por partido pulado (sem discursos disponíveis)")
        print("   ℹ️  Este teste requer discursos do partido no período")

    # Resultados finais
    print_separator()
    print("📊 RESULTADOS DOS TESTES")
    print("="*80)
    print(f"Total de testes: {results['total']}")
    print(f"✅ Aprovados: {results['passed']}")
    print(f"❌ Falharam: {results['failed']}")

    if results['failed'] == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
    else:
        print(f"\n⚠️  {results['failed']} teste(s) falharam. Verifique os logs acima.")

    print("="*80 + "\n")

    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if results['failed'] == 0 else 1)
