#!/bin/bash

# Script de instalação limpa para a API

echo "======================================"
echo "INSTALAÇÃO DA API - CÂMARA DOS DEPUTADOS"
echo "======================================"

# Remove o ambiente virtual existente se houver
if [ -d ".venv" ]; then
    echo ""
    echo "🗑️  Removendo ambiente virtual antigo..."
    rm -rf .venv
fi

# Cria novo ambiente virtual
echo ""
echo "📦 Criando novo ambiente virtual..."
python3 -m venv .venv

# Ativa o ambiente virtual
echo ""
echo "✅ Ativando ambiente virtual..."
source .venv/bin/activate

# Atualiza pip
echo ""
echo "⬆️  Atualizando pip..."
pip install --upgrade pip

# Instala as dependências
echo ""
echo "📥 Instalando dependências..."
pip install -r requirements.txt

# Baixa dados do NLTK
echo ""
echo "📚 Baixando dados do NLTK..."
python setup.py

echo ""
echo "======================================"
echo "✅ INSTALAÇÃO CONCLUÍDA!"
echo "======================================"
echo ""
echo "Para iniciar a API, execute:"
echo "  source .venv/bin/activate"
echo "  uvicorn main:app --reload"
echo ""
