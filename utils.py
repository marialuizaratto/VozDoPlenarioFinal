"""
Utilitários para processamento de texto e geração de nuvem de palavras
"""
import io
import re
from typing import List, Dict, Any, Set
from wordcloud import WordCloud
from matplotlib import pyplot as plt
from PIL import Image
import nltk
import os
import json
import time


# Cache interno das stopwords (carregado sob demanda, não na importação do módulo)
_STOPWORDS_PT: Set[str] = None


def _get_stopwords() -> Set[str]:
    """
    Obtém as stopwords em português do NLTK
    Baixa os dados se necessário
    """
    try:
        # Tenta usar as stopwords já baixadas
        from nltk.corpus import stopwords
        stopwords_set = set(stopwords.words('portuguese'))
    except LookupError:
        # Se não estiver baixado, baixa automaticamente
        print("Baixando stopwords do NLTK...")
        try:
            nltk.download('stopwords', quiet=True)
            from nltk.corpus import stopwords
            stopwords_set = set(stopwords.words('portuguese'))
            print("Stopwords baixadas com sucesso!")
        except Exception as e:
            # Fallback para stopwords mínimas caso o download falhe
            print(f"Aviso: Não foi possível baixar stopwords do NLTK ({e}), usando fallback")
            stopwords_set = {
                'a', 'o', 'e', 'de', 'da', 'do', 'em', 'um', 'uma', 'os', 'as', 'dos', 'das',
                'para', 'com', 'por', 'que', 'se', 'na', 'no', 'ao', 'aos', 'seu', 'sua',
                'mais', 'foi', 'ser', 'está', 'são', 'como', 'mas', 'muito', 'também', 'tem',
                'ou', 'quando', 'ainda', 'sobre', 'até', 'entre', 'sem', 'isso', 'só', 'pode'
            }

    # Adiciona stopwords específicas do contexto político
    additional_stopwords = {
        'senhor', 'senhora', 'presidente', 'sr', 'sra', 'deputado', 'deputada',
        'excelência', 'vossa', 'câmara', 'casa', 'brasil', 'brasileiro', 'brasileira',
        'vai', 'dizer', 'falar', 'aqui', 'agora', 'hoje', 'ontem', 'ano', 'dia',
        'vez', 'vezes', 'ser', 'estar', 'ter', 'fazer', 'poder', 'querer', 'ir'
    }

    stopwords_set.update(additional_stopwords)
    return stopwords_set


def get_stopwords_pt() -> Set[str]:
    """
    Retorna as stopwords em português, carregando (e baixando, se preciso)
    apenas na primeira vez que forem usadas. Evita atraso na inicialização
    do servidor (importante para o health check do Render).
    """
    global _STOPWORDS_PT
    if _STOPWORDS_PT is None:
        _STOPWORDS_PT = _get_stopwords()
    return _STOPWORDS_PT


def clean_text(text: str) -> str:
    """
    Limpa o texto removendo caracteres especiais e normalizando espaços
    """
    if not text:
        return ""

    # Remove caracteres especiais mantendo apenas letras, números e espaços
    text = re.sub(r'[^\w\s]', ' ', text)

    # Normaliza espaços múltiplos
    text = re.sub(r'\s+', ' ', text)

    return text.strip().lower()


def extract_text_from_speeches(speeches: List[Dict[str, Any]]) -> str:
    """
    Extrai e concatena o texto de múltiplos discursos
    """
    texts = []
    for speech in speeches:
        transcricao = speech.get("transcricao", "")
        sumario = speech.get("sumario", "")
        keywords = speech.get("keywords", "")

        combined = f"{transcricao} {sumario} {keywords}"
        if combined.strip():
            texts.append(clean_text(combined))

    return " ".join(texts)


def generate_wordcloud_image(text: str, width: int = 800, height: int = 600) -> bytes:
    """
    Gera uma imagem de nuvem de palavras a partir do texto

    Args:
        text: Texto para gerar a nuvem de palavras
        width: Largura da imagem
        height: Altura da imagem

    Returns:
        Bytes da imagem PNG
    """
    if not text or not text.strip():
        # Retorna imagem vazia se não houver texto
        fig, ax = plt.subplots(figsize=(width/100, height/100))
        ax.text(0.5, 0.5, 'Sem dados disponíveis',
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=20)
        ax.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        buf.seek(0)
        return buf.read()

    # Gera a nuvem de palavras (stopwords carregadas sob demanda aqui)
    wordcloud = WordCloud(
        width=width,
        height=height,
        background_color='white',
        stopwords=get_stopwords_pt(),
        max_words=200,
        relative_scaling=0.5,
        min_font_size=10,
        colormap='viridis'
    ).generate(text)

    # Cria a imagem
    fig, ax = plt.subplots(figsize=(width/100, height/100))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')

    # Salva em buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close()
    buf.seek(0)

    return buf.read()

def load_cache(cache_key: str, cache_dir: str, expiration_minutes: int = 0) -> Any:
    """Loads data from cache if available and not expired."""
    cache_path = os.path.join(cache_dir, f"{cache_key}.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if expiration_minutes > 0:
            cache_timestamp = os.path.getmtime(cache_path)
            if (time.time() - cache_timestamp) / 60 < expiration_minutes:
                return data
            else:
                os.remove(cache_path) # Cache expired, remove it
        else:
            return data
    return None

def save_cache(cache_key: str, data: Any, cache_dir: str):
    """Saves data to cache."""
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{cache_key}.json")
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
