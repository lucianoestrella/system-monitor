#!/bin/bash
# ============================================================================
# INSTALL.SH - System Monitor
# Script de instalação automática para Linux
# ============================================================================

echo "============================================"
echo "  System Monitor - Instalação Automática"
echo "============================================"
echo ""

# Verifica se Python3 está instalado
if ! command -v python3 &> /dev/null
then
    echo "❌ Python3 não encontrado!"
    echo "   Instale o Python3 primeiro:"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "   Fedora: sudo dnf install python3 python3-pip"
    echo "   Arch: sudo pacman -S python python-pip"
    exit 1
fi

echo "✓ Python3 encontrado: $(python3 --version)"
echo ""

# Cria ambiente virtual
echo "📦 Criando ambiente virtual..."
if [ -d ".venv" ]; then
    echo "⚠️  Ambiente virtual já existe. Removendo..."
    rm -rf .venv
fi

python3 -m venv .venv

if [ $? -ne 0 ]; then
    echo "❌ Erro ao criar ambiente virtual!"
    exit 1
fi

echo "✓ Ambiente virtual criado"
echo ""

# Ativa ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source .venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Erro ao ativar ambiente virtual!"
    exit 1
fi

echo "✓ Ambiente virtual ativado"
echo ""

# Atualiza pip
echo "⬆️  Atualizando pip..."
pip install --upgrade pip --quiet

# Instala dependências
echo "📥 Instalando dependências..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Erro ao instalar dependências!"
        exit 1
    fi
else
    echo "⚠️  requirements.txt não encontrado. Instalando dependências básicas..."
    pip install psutil rich customtkinter
fi

echo ""
echo "============================================"
echo "  ✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "============================================"
echo ""
echo "Para usar o System Monitor:"
echo ""
echo "1. Ative o ambiente virtual:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Execute o programa:"
echo "   python3 main.py          # Modo padrão (GUI)"
echo "   python3 main.py --cli    # Modo CLI"
echo "   python3 gui.py           # Apenas GUI"
echo "   python3 cli.py           # Apenas CLI"
echo ""
echo "3. Para desativar o ambiente virtual:"
echo "   deactivate"
echo ""
echo "============================================"