#!/bin/bash
# ============================================================================
# UNINSTALL.SH - System Monitor
# Script de desinstalação para Linux
# ============================================================================

echo "============================================"
echo "  System Monitor - Desinstalação"
echo "============================================"
echo ""
echo "⚠️  ATENÇÃO: Este script irá remover:"
echo "   - Ambiente virtual (.venv/)"
echo "   - Arquivos cache Python (__pycache__, *.pyc)"
echo "   - Arquivos temporários do PyInstaller (build/, dist/, *.spec)"
echo ""
echo "   Os relatórios gerados (reports/) NÃO serão removidos."
echo ""

# Pergunta confirmação
read -p "Deseja continuar? (s/N): " confirm
if [[ ! "$confirm" =~ ^[sS]$ ]]; then
    echo ""
    echo "❌ Desinstalação cancelada."
    exit 0
fi

echo ""
echo "🗑️  Iniciando desinstalação..."
echo ""

# Remove ambiente virtual
if [ -d ".venv" ]; then
    echo "🗑️  Removendo ambiente virtual..."
    rm -rf .venv
    echo "✓ Ambiente virtual removido"
else
    echo "⚠️  Ambiente virtual não encontrado"
fi

# Remove cache Python
echo "🗑️  Removendo cache Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null
echo "✓ Cache Python removido"

# Remove arquivos do PyInstaller
if [ -d "build" ] || [ -d "dist" ] || [ -f "*.spec" ]; then
    echo "🗑️  Removendo arquivos do PyInstaller..."
    rm -rf build dist *.spec 2>/dev/null
    echo "✓ Arquivos do PyInstaller removidos"
fi

# Remove arquivos de teste
if [ -f "teste.py" ] || [ -f "teste_utf8.pdf" ] || [ -f "gerar_pdf_teste.py" ]; then
    echo "🗑️  Removendo arquivos de teste..."
    rm -f teste.py teste_utf8.pdf gerar_pdf_teste.py 2>/dev/null
    echo "✓ Arquivos de teste removidos"
fi

echo ""
echo "============================================"
echo "  ✅ DESINSTALAÇÃO CONCLUÍDA!"
echo "============================================"
echo ""
echo "📁 Os seguintes itens foram PRESERVADOS:"
echo "   - Código fonte (.py)"
echo "   - Relatórios gerados (reports/)"
echo "   - Scripts de instalação (install.sh, requirements.txt)"
echo ""
echo "Para reinstalar, execute:"
echo "   ./install.sh"
echo ""
echo "Para remover TUDO (incluindo código fonte):"
echo "   cd .."
echo "   rm -rf system_monitor/"
echo ""
echo "============================================"