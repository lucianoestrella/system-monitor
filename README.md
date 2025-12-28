# 🖥️ System Monitor

**Sistema completo de monitoramento e análise forense de hardware e software**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

Sistema modular de monitoramento em tempo real com interface gráfica moderna (GUI) e interface de linha de comando (CLI), incluindo testes de stress, auditoria de segurança e geração de relatórios forenses completos.

---

## 📋 Índice

- [Características](#-características)
- [Capturas de Tela](#-capturas-de-tela)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
  - [Instalação Automática](#instalação-automática-recomendado)
  - [Instalação Manual](#instalação-manual)
- [Uso](#-uso)
  - [Modo GUI](#modo-gui-interface-gráfica)
  - [Modo CLI](#modo-cli-terminal)
- [Funcionalidades](#-funcionalidades)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Geração de Executáveis](#-geração-de-executáveis)
- [Desinstalação](#-desinstalação)
- [Compatibilidade](#-compatibilidade)
- [Solução de Problemas](#-solução-de-problemas)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)
- [Autor](#-autor)

---

## ✨ Características

### 🎨 Interface Moderna
- **GUI (Interface Gráfica)**: Interface moderna com CustomTkinter, tema escuro, cards organizados
- **CLI (Terminal)**: Interface colorida e formatada com Rich, menus interativos

### 📊 Monitoramento em Tempo Real
- **CPU**: Uso, frequência, núcleos físicos/lógicos, temperatura
- **RAM**: Uso, disponível, total, percentual
- **GPU**: Informações de placas NVIDIA (temperatura, uso, memória)
- **Discos**: Uso, espaço livre, partições, temperatura (Linux com smartctl)
- **Rede**: Interfaces, endereços IP, bytes enviados/recebidos, status
- **Bateria**: Percentual, status de carga, tempo restante (notebooks)

### 🔥 Testes de Stress
- **Stress de CPU**: Teste de carga com múltiplos threads
- **Stress de RAM**: Alocação e manipulação de memória
- Monitoramento de temperatura e uso durante os testes

### 🔒 Auditoria de Segurança
- **Auditoria de Processos**: Lista processos suspeitos ou com alto uso
- **Detecção de Overclock**: Identifica ferramentas de overclock em execução
- **Anomalias de Rede**: Detecta conexões suspeitas ou portas abertas

### 📄 Relatórios Forenses
- **Formato TXT**: Relatórios completos em texto puro
- **Snapshot Completo**: Sistema, hardware, rede, stress tests, segurança
- **Portabilidade**: Arquivos universais, sem problemas de encoding

---

## 📸 Capturas de Tela

### Interface Gráfica (GUI)

┌─────────────────────────────────────────────────────────┐
│ System Monitor ─ □ ×│
├─────────────────────────────────────────────────────────┤
│ [Hardware] [Stress] [Segurança] [Relatórios] │
├─────────────────────────────────────────────────────────┤
│ ╔═══════════════════════════════════════════════════╗ │
│ ║ CPU ║ │
│ ║ Uso: 45.2% Frequência: 3.6 GHz ║ │
│ ║ Núcleos: 8 (4 físicos) ║ │
│ ╚═══════════════════════════════════════════════════╝ │
│ ╔═══════════════════════════════════════════════════╗ │
│ ║ RAM ║ │
│ ║ Usado: 8.5 GB / 16.0 GB (53.1%) ║ │
│ ╚═══════════════════════════════════════════════════╝ │
└─────────────────────────────────────────────────────────┘


### Interface CLI (Terminal)
╔══════════════════════════════════════════════════════════╗
║ SYSTEM MONITOR - MENU PRINCIPAL ║
╚══════════════════════════════════════════════════════════╝

[1] 📊 Monitoramento de Hardware
[2] 🔥 Testes de Stress
[3] 🔒 Auditoria de Segurança
[4] 📄 Gerar Relatório Forense
[0] ❌ Sair

Escolha uma opção:


---

## 🔧 Requisitos

### Sistema Operacional
- **Windows**: 10/11 (64-bit)
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, Arch Linux

### Software
- **Python**: 3.8 ou superior
- **pip**: Gerenciador de pacotes Python

### Dependências Python
- `psutil` >= 5.9.0 - Monitoramento de sistema
- `rich` >= 13.0.0 - Interface CLI
- `customtkinter` >= 5.0.0 - Interface GUI

### Ferramentas Externas (Opcional)
- **Linux**: `smartctl` (smartmontools) - Para temperatura de discos
  ```bash
  sudo apt install smartmontools  # Ubuntu/Debian
  sudo dnf install smartmontools  # Fedora

  👤 Autor
LUCIANO ESTRELLA

🌐 Website: https://lucianoestrella.com.br
📧 Email: programador@lucianoestrella.com.br
💼 LinkedIn: [seu-linkedin](https://www.linkedin.com/in/lucianoestrella/)
🐙 GitHub: https://github.com/lucianoestrella
🙏 Agradecimentos
psutil - Biblioteca de monitoramento
Rich - Interface CLI elegante
CustomTkinter - GUI moderna
Comunidade Python 🐍
📊 Status do Projeto