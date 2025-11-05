"""
Script de configuração inicial da API
Baixa os dados necessários do NLTK
"""
import nltk
import sys


def download_nltk_data():
    """
    Baixa os dados necessários do NLTK
    """
    print("="*60)
    print("CONFIGURAÇÃO INICIAL - API da Câmara dos Deputados")
    print("="*60)
    print("\n📦 Baixando dados do NLTK...")

    try:
        # Baixa as stopwords
        print("\n⬇️  Baixando stopwords em português...")
        nltk.download('stopwords', quiet=False)

        # Verifica se foi instalado corretamente
        from nltk.corpus import stopwords
        pt_stopwords = stopwords.words('portuguese')

        print(f"\n✅ Stopwords instaladas com sucesso!")
        print(f"   Total de stopwords em português: {len(pt_stopwords)}")
        print(f"   Exemplos: {', '.join(list(pt_stopwords)[:10])}")

        print("\n" + "="*60)
        print("✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*60)
        print("\n🚀 Você pode agora iniciar a API com:")
        print("   uvicorn main:app --reload")
        print("\nOu simplesmente:")
        print("   python main.py")
        print("\n")

        return True

    except Exception as e:
        print(f"\n❌ Erro ao baixar dados do NLTK: {e}")
        print("\n⚠️  A API ainda funcionará, mas usará uma lista básica de stopwords.")
        print("   Você pode tentar novamente executando este script.")
        return False


if __name__ == "__main__":
    success = download_nltk_data()
    sys.exit(0 if success else 1)
