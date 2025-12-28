# file: gui.py
"""
Interface Gráfica (GUI) usando CustomTkinter para o System Monitor.

Funcionalidades:
- Dashboard com métricas de CPU, RAM, GPU, Discos, Rede e Bateria
- Stress Tests (CPU, RAM e PESADO)
- Auditoria de Segurança
- Monitoramento de Rede (scan de hosts, portas, conexões)
- Detecção de acessos remotos e anomalias de segurança de rede
- Geração de Relatório Forense COMPLETO (Máquina / Rede / Full) em TXT e PDF
- Módulo de Emergência (Desligamento, Colapso, Limpeza, Controle Remoto)
"""

import customtkinter as ctk
import threading
import time
import socket
import os
import platform
from datetime import datetime
from typing import Optional

from hw_monitor import get_system_snapshot
from stress import start_cpu_stress, start_ram_stress, start_full_stress
from security import (
    full_security_scan,
    check_network_spikes,
    detect_ssh_bruteforce_linux,
)
from network_monitor import (
    guess_local_network_cidr,
    scan_network_hosts,
    scan_host_ports,
    list_local_connections,
    list_remote_access_sessions,
    detect_remote_login_bruteforce_from_conns,
)

from emergency import (
    shutdown_system,
    schedule_shutdown as emergency_schedule_shutdown,
    cancel_scheduled_shutdown as emergency_cancel_scheduled_shutdown,
    SystemCollapser,
    clean_sensitive_logs,
    lock_current_user,
    RemoteControlServer,
)

# ✅ IMPORTA AS NOVAS FUNÇÕES DE RELATÓRIO COMPLETO
from report import (
    generate_full_forensic_report,
)

# Configuração do tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SystemMonitorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("System Monitor - Dashboard")
        self.geometry("1100x750")
        
        # Flag para controlar o fechamento
        self._is_closing = False
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Criar abas
        self.tabview = ctk.CTkTabview(self, width=1050, height=700)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        # Adicionar abas
        self.tabview.add("Dashboard")
        self.tabview.add("Stress Test")
        self.tabview.add("Segurança")
        self.tabview.add("Rede")
        self.tabview.add("Relatório Forense")
        self.tabview.add(" ⚠️ Emergência")

        # Configurar cada aba
        self.setup_dashboard_tab()
        self.setup_stress_tab()
        self.setup_security_tab()
        self.setup_network_tab()
        self.setup_forensic_tab()
        self.setup_emergency_tab()

        # Thread de atualização do dashboard
        self.update_thread = None
        self.start_dashboard_updates()

    def setup_dashboard_tab(self):
        """Configura a aba de Dashboard."""
        tab = self.tabview.tab("Dashboard")

        # Frame principal com scroll
        self.dashboard_frame = ctk.CTkScrollableFrame(tab, width=1000, height=650)
        self.dashboard_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Cards para cada seção
        self.cpu_card = self.create_card(self.dashboard_frame, "CPU & RAM")
        self.gpu_card = self.create_card(self.dashboard_frame, "GPU")
        self.disk_card = self.create_card(self.dashboard_frame, "Discos")
        self.network_card = self.create_card(self.dashboard_frame, "Rede")
        self.battery_card = self.create_card(self.dashboard_frame, "Bateria")

    def setup_stress_tab(self):
        """Configura a aba de Stress Test."""
        tab = self.tabview.tab("Stress Test")

        # Frame principal com scroll
        main_frame = ctk.CTkScrollableFrame(tab, width=1000, height=650)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Card CPU Stress
        cpu_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        cpu_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            cpu_frame,
            text="Stress Test - CPU",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        # Inputs CPU
        input_frame_cpu = ctk.CTkFrame(cpu_frame, fg_color="transparent")
        input_frame_cpu.pack(pady=10)

        ctk.CTkLabel(input_frame_cpu, text="Threads:", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.cpu_threads_entry = ctk.CTkEntry(input_frame_cpu, width=100)
        self.cpu_threads_entry.insert(0, "4")
        self.cpu_threads_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(input_frame_cpu, text="Intensidade (0.1-1.0):", font=("Roboto", 14)).grid(
            row=1, column=0, padx=10, pady=5, sticky="e"
        )
        self.cpu_intensity_entry = ctk.CTkEntry(input_frame_cpu, width=100)
        self.cpu_intensity_entry.insert(0, "1.0")
        self.cpu_intensity_entry.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(input_frame_cpu, text="Duração (s):", font=("Roboto", 14)).grid(
            row=2, column=0, padx=10, pady=5, sticky="e"
        )
        self.cpu_duration_entry = ctk.CTkEntry(input_frame_cpu, width=100)
        self.cpu_duration_entry.insert(0, "30")
        self.cpu_duration_entry.grid(row=2, column=1, padx=10, pady=5)

        self.cpu_stress_btn = ctk.CTkButton(
            cpu_frame,
            text="Iniciar Stress de CPU",
            command=self.run_cpu_stress,
            fg_color="#d97706",
            hover_color="#b45309",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.cpu_stress_btn.pack(pady=(10, 15))

        # Card RAM Stress
        ram_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        ram_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            ram_frame,
            text="Stress Test - RAM",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        # Inputs RAM
        input_frame_ram = ctk.CTkFrame(ram_frame, fg_color="transparent")
        input_frame_ram.pack(pady=10)

        ctk.CTkLabel(input_frame_ram, text="Memória (MB):", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.ram_mb_entry = ctk.CTkEntry(input_frame_ram, width=100)
        self.ram_mb_entry.insert(0, "512")
        self.ram_mb_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(input_frame_ram, text="Duração (s):", font=("Roboto", 14)).grid(
            row=1, column=0, padx=10, pady=5, sticky="e"
        )
        self.ram_duration_entry = ctk.CTkEntry(input_frame_ram, width=100)
        self.ram_duration_entry.insert(0, "30")
        self.ram_duration_entry.grid(row=1, column=1, padx=10, pady=5)

        self.ram_stress_btn = ctk.CTkButton(
            ram_frame,
            text="Iniciar Stress de RAM",
            command=self.run_ram_stress,
            fg_color="#dc2626",
            hover_color="#991b1b",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.ram_stress_btn.pack(pady=(10, 15))

        # Card STRESS PESADO (CPU + RAM)
        full_frame = ctk.CTkFrame(main_frame, fg_color="#7f1d1d", corner_radius=15, border_width=2, border_color="#dc2626")
        full_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            full_frame,
            text="⚠️  STRESS PESADO (CPU + RAM)  ⚠️",
            font=("Roboto", 20, "bold"),
            text_color="#fca5a5",
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            full_frame,
            text="ATENÇÃO: Usa TODOS os núcleos da CPU + ~60% da RAM",
            font=("Roboto", 11),
            text_color="#fbbf24",
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            full_frame,
            text="Pode deixar o sistema MUITO lento durante o teste!",
            font=("Roboto", 11),
            text_color="#fbbf24",
        ).pack(pady=(0, 10))

        # Inputs Stress Pesado
        input_frame_full = ctk.CTkFrame(full_frame, fg_color="transparent")
        input_frame_full.pack(pady=10)

        ctk.CTkLabel(input_frame_full, text="Duração (s, máx 600):", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.full_duration_entry = ctk.CTkEntry(input_frame_full, width=100)
        self.full_duration_entry.insert(0, "60")
        self.full_duration_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(input_frame_full, text="Intensidade CPU (0.1-1.0):", font=("Roboto", 14)).grid(
            row=1, column=0, padx=10, pady=5, sticky="e"
        )
        self.full_intensity_entry = ctk.CTkEntry(input_frame_full, width=100)
        self.full_intensity_entry.insert(0, "1.0")
        self.full_intensity_entry.grid(row=1, column=1, padx=10, pady=5)

        self.full_stress_btn = ctk.CTkButton(
            full_frame,
            text="🔥 INICIAR STRESS PESADO 🔥",
            command=self.run_full_stress,
            fg_color="#991b1b",
            hover_color="#7f1d1d",
            height=45,
            font=("Roboto", 15, "bold"),
            text_color="#fca5a5",
        )
        self.full_stress_btn.pack(pady=(10, 15))

    def setup_security_tab(self):
        """Configura a aba de Segurança."""
        tab = self.tabview.tab("Segurança")

        # Frame principal
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Card de controles
        control_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        control_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            control_frame,
            text="Auditoria de Segurança",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        self.security_btn = ctk.CTkButton(
            control_frame,
            text="Executar Varredura",
            command=self.run_security_scan,
            fg_color="#dc2626",
            hover_color="#991b1b",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.security_btn.pack(pady=(10, 15))

        # Card de resultados
        result_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        result_frame.pack(padx=20, pady=10, fill="both", expand=True)

        ctk.CTkLabel(
            result_frame,
            text="Resultados",
            font=("Roboto", 16, "bold"),
        ).pack(pady=(15, 10))

        self.security_textbox = ctk.CTkTextbox(
            result_frame,
            width=900,
            height=400,
            font=("Consolas", 12),
        )
        self.security_textbox.pack(padx=15, pady=(0, 15), fill="both", expand=True)

    def setup_network_tab(self):
        """Configura a aba de Monitoramento de Rede."""
        tab = self.tabview.tab("Rede")

        # Frame principal com scroll
        main_frame = ctk.CTkScrollableFrame(tab, width=1000, height=650)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Card 1: Scan de Rede
        scan_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        scan_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            scan_frame,
            text="Descobrir Hosts na Rede Local",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        self.scan_network_btn = ctk.CTkButton(
            scan_frame,
            text="Escanear Rede",
            command=self.scan_network,
            fg_color="#22c55e",
            hover_color="#16a34a",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.scan_network_btn.pack(pady=(10, 15))

        self.network_hosts_textbox = ctk.CTkTextbox(
            scan_frame,
            width=900,
            height=150,
            font=("Consolas", 12),
        )
        self.network_hosts_textbox.pack(padx=15, pady=(0, 15), fill="both", expand=True)

        # Card 2: Port Scan
        port_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        port_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            port_frame,
            text="Escanear Portas de um Host",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        input_frame = ctk.CTkFrame(port_frame, fg_color="transparent")
        input_frame.pack(pady=10)

        ctk.CTkLabel(input_frame, text="IP do Host:", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.port_scan_ip_entry = ctk.CTkEntry(input_frame, width=200)
        self.port_scan_ip_entry.insert(0, "192.168.0.1")
        self.port_scan_ip_entry.grid(row=0, column=1, padx=10, pady=5)

        self.port_scan_btn = ctk.CTkButton(
            port_frame,
            text="Escanear Portas",
            command=self.scan_ports,
            fg_color="#3b82f6",
            hover_color="#1d4ed8",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.port_scan_btn.pack(pady=(10, 15))

        self.port_scan_textbox = ctk.CTkTextbox(
            port_frame,
            width=900,
            height=150,
            font=("Consolas", 12),
        )
        self.port_scan_textbox.pack(padx=15, pady=(0, 15), fill="both", expand=True)

        # Card 3: Conexões Locais
        conn_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        conn_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            conn_frame,
            text="Conexões Locais (Netstat)",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        self.netstat_btn = ctk.CTkButton(
            conn_frame,
            text="Ver Conexões",
            command=self.show_netstat,
            fg_color="#8b5cf6",
            hover_color="#6d28d9",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.netstat_btn.pack(pady=(10, 15))

        self.netstat_textbox = ctk.CTkTextbox(
            conn_frame,
            width=900,
            height=200,
            font=("Consolas", 11),
        )
        self.netstat_textbox.pack(padx=15, pady=(0, 15), fill="both", expand=True)

        # Card 4: Acesso Remoto
        remote_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        remote_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            remote_frame,
            text="Acesso Remoto (RDP / SSH)",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        # RDP
        rdp_input_frame = ctk.CTkFrame(remote_frame, fg_color="transparent")
        rdp_input_frame.pack(pady=10)

        ctk.CTkLabel(rdp_input_frame, text="IP para RDP:", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.rdp_ip_entry = ctk.CTkEntry(rdp_input_frame, width=200)
        self.rdp_ip_entry.insert(0, "192.168.0.1")
        self.rdp_ip_entry.grid(row=0, column=1, padx=10, pady=5)

        self.rdp_btn = ctk.CTkButton(
            rdp_input_frame,
            text="Abrir RDP",
            command=self.open_rdp,
            fg_color="#f59e0b",
            hover_color="#d97706",
            height=35,
            width=150,
            font=("Roboto", 13, "bold"),
        )
        self.rdp_btn.grid(row=0, column=2, padx=10, pady=5)

        # SSH
        ssh_input_frame = ctk.CTkFrame(remote_frame, fg_color="transparent")
        ssh_input_frame.pack(pady=10)

        ctk.CTkLabel(ssh_input_frame, text="IP para SSH:", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.ssh_ip_entry = ctk.CTkEntry(ssh_input_frame, width=200)
        self.ssh_ip_entry.insert(0, "192.168.0.1")
        self.ssh_ip_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(ssh_input_frame, text="Usuário:", font=("Roboto", 14)).grid(
            row=1, column=0, padx=10, pady=5, sticky="e"
        )
        self.ssh_user_entry = ctk.CTkEntry(ssh_input_frame, width=200)
        self.ssh_user_entry.insert(0, "root")
        self.ssh_user_entry.grid(row=1, column=1, padx=10, pady=5)

        self.ssh_btn = ctk.CTkButton(
            ssh_input_frame,
            text="Abrir SSH",
            command=self.open_ssh,
            fg_color="#10b981",
            hover_color="#059669",
            height=35,
            width=150,
            font=("Roboto", 13, "bold"),
        )
        self.ssh_btn.grid(row=0, column=2, rowspan=2, padx=10, pady=5)

        ctk.CTkLabel(remote_frame, text="", font=("Roboto", 10)).pack(pady=(0, 10))

        # Card 5: Segurança de Rede / Anomalias
        security_net_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        security_net_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            security_net_frame,
            text="🔒 Segurança de Rede / Anomalias",
            font=("Roboto", 18, "bold"),
        ).pack(pady=(15, 10))

        ctk.CTkLabel(
            security_net_frame,
            text="Detecta sessões remotas ativas, picos de tráfego e tentativas de brute-force",
            font=("Roboto", 11),
            text_color="#94a3b8",
        ).pack(pady=(0, 10))

        self.analyze_security_btn = ctk.CTkButton(
            security_net_frame,
            text="Analisar Acessos Remotos e Anomalias",
            command=self.analyze_network_security,
            fg_color="#dc2626",
            hover_color="#991b1b",
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.analyze_security_btn.pack(pady=(10, 15))

        self.security_net_textbox = ctk.CTkTextbox(
            security_net_frame,
            width=900,
            height=300,
            font=("Consolas", 11),
        )
        self.security_net_textbox.pack(padx=15, pady=(0, 15), fill="both", expand=True)

    def setup_forensic_tab(self):
        """Configura a aba de Relatório Forense COMPLETO."""
        tab = self.tabview.tab("Relatório Forense")

        # Frame principal
        main_frame = ctk.CTkFrame(tab)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Card de controles
        control_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        control_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            control_frame,
            text="📋 Geração de Relatório Forense COMPLETO",
            font=("Roboto", 20, "bold"),
        ).pack(pady=(15, 10))

        ctk.CTkLabel(
            control_frame,
            text="Gera relatório forense completo com TODAS as informações: hardware, rede, stress tests e segurança.",
            font=("Roboto", 12),
            text_color="#94a3b8",
        ).pack(pady=(0, 20))

        # ✅ OPÇÕES DE CONFIGURAÇÃO DO RELATÓRIO
        options_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        options_frame.pack(pady=(0, 15))

        ctk.CTkLabel(
            options_frame,
            text="Opções do Relatório:",
            font=("Roboto", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Checkbox: Incluir Stress Tests
        self.include_stress_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame,
            text="Incluir Stress Tests (CPU e RAM)",
            variable=self.include_stress_var,
            font=("Roboto", 12),
        ).grid(row=1, column=0, padx=10, pady=5, sticky="w")

        # Checkbox: Incluir Auditoria de Segurança
        self.include_security_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame,
            text="Incluir Auditoria de Segurança",
            variable=self.include_security_var,
            font=("Roboto", 12),
        ).grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Input: Duração dos Stress Tests
        ctk.CTkLabel(options_frame, text="Duração dos Stress Tests (s):", font=("Roboto", 12)).grid(
            row=2, column=0, padx=10, pady=5, sticky="e"
        )
        self.stress_duration_entry = ctk.CTkEntry(options_frame, width=100)
        self.stress_duration_entry.insert(0, "5")
        self.stress_duration_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Separador
        ctk.CTkLabel(control_frame, text="", font=("Roboto", 6)).pack()

        
        self.forensic_txt_btn = ctk.CTkButton(
            control_frame,
            text="📄 Gerar Relatório TXT Completo",
            command=self.generate_forensic_txt,
            fg_color="#3b82f6",
            hover_color="#1d4ed8",
            height=45,
            width=400,
            font=("Roboto", 15, "bold"),
        )
        self.forensic_txt_btn.pack(pady=(0, 15))

        # Card de resultados
        result_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        result_frame.pack(padx=20, pady=10, fill="both", expand=True)

        ctk.CTkLabel(
            result_frame,
            text="Status / Prévia",
            font=("Roboto", 16, "bold"),
        ).pack(pady=(15, 10))

        self.forensic_textbox = ctk.CTkTextbox(
            result_frame,
            width=900,
            height=400,
            font=("Consolas", 11),
        )
        self.forensic_textbox.pack(padx=15, pady=(0, 15), fill="both", expand=True)
        self.forensic_textbox.insert(
            "1.0",
            "Aguardando geração de relatório...\n\n"
            "Configure as opções acima e clique em um dos botões para gerar.\n\n"
            "✓ TXT: Relatório completo em texto puro\n"
        )

    def setup_emergency_tab(self):
        """Configura a aba de Emergência."""
        tab = self.tabview.tab(" ⚠️ Emergência")

        # Frame principal com scroll
        main_frame = ctk.CTkScrollableFrame(tab, width=1000, height=650)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Card 1: Desligamento do Sistema
        shutdown_frame = ctk.CTkFrame(main_frame, fg_color="#7f1d1d", corner_radius=15, border_width=2, border_color="#dc2626")
        shutdown_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            shutdown_frame,
            text="⚡ Desligamento do Sistema",
            font=("Roboto", 20, "bold"),
            text_color="#fca5a5",
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            shutdown_frame,
            text="ATENÇÃO: Esta operação desligará o computador!",
            font=("Roboto", 12),
            text_color="#fbbf24",
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            shutdown_frame,
            text="Certifique-se de salvar todos os trabalhos antes de continuar.",
            font=("Roboto", 11),
            text_color="#fbbf24",
        ).pack(pady=(0, 15))

        # Botões de desligamento
        shutdown_btn_frame = ctk.CTkFrame(shutdown_frame, fg_color="transparent")
        shutdown_btn_frame.pack(pady=10)

        self.shutdown_now_btn = ctk.CTkButton(
            shutdown_btn_frame,
            text="Desligar Agora",
            command=self.shutdown_now,
            fg_color="#dc2626",
            hover_color="#991b1b",
            height=40,
            width=200,
            font=("Roboto", 14, "bold"),
        )
        self.shutdown_now_btn.grid(row=0, column=0, padx=10, pady=5)

        self.shutdown_cancel_btn = ctk.CTkButton(
            shutdown_btn_frame,
            text="Cancelar Desligamento Programado",
            command=self.cancel_scheduled_shutdown,
            fg_color="#3b82f6",
            hover_color="#1d4ed8",
            height=40,
            width=250,
            font=("Roboto", 14, "bold"),
        )
        self.shutdown_cancel_btn.grid(row=0, column=1, padx=10, pady=5)

        # Input para desligamento programado
        schedule_frame = ctk.CTkFrame(shutdown_frame, fg_color="transparent")
        schedule_frame.pack(pady=10)

        ctk.CTkLabel(schedule_frame, text="Desligar em (minutos):", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.shutdown_minutes_entry = ctk.CTkEntry(schedule_frame, width=100)
        self.shutdown_minutes_entry.insert(0, "10")
        self.shutdown_minutes_entry.grid(row=0, column=1, padx=10, pady=5)

        self.shutdown_schedule_btn = ctk.CTkButton(
            schedule_frame,
            text="Programar Desligamento",
            command=self.schedule_shutdown,
            fg_color="#d97706",
            hover_color="#b45309",
            height=35,
            width=200,
            font=("Roboto", 13, "bold"),
        )
        self.shutdown_schedule_btn.grid(row=0, column=2, padx=10, pady=5)

        ctk.CTkLabel(shutdown_frame, text="", font=("Roboto", 10)).pack(pady=(0, 15))

        # Card 2: Colapso do Sistema
        collapse_frame = ctk.CTkFrame(main_frame, fg_color="#7f1d1d", corner_radius=15, border_width=2, border_color="#dc2626")
        collapse_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            collapse_frame,
            text="💥 Colapso do Sistema (Teste de Estabilidade)",
            font=("Roboto", 20, "bold"),
            text_color="#fca5a5",
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            collapse_frame,
            text="ATENÇÃO: Esta operação pode travar ou reiniciar o sistema!",
            font=("Roboto", 12),
            text_color="#fbbf24",
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            collapse_frame,
            text="Use apenas para testes de estabilidade em ambientes controlados.",
            font=("Roboto", 11),
            text_color="#fbbf24",
        ).pack(pady=(0, 10))

        # Intensidade do colapso
        intensity_frame = ctk.CTkFrame(collapse_frame, fg_color="transparent")
        intensity_frame.pack(pady=10)

        ctk.CTkLabel(intensity_frame, text="Intensidade:", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.collapse_intensity_var = ctk.StringVar(value="leve")
        ctk.CTkRadioButton(
            intensity_frame,
            text="Leve (CPU + RAM moderado)",
            variable=self.collapse_intensity_var,
            value="leve",
            font=("Roboto", 12),
        ).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkRadioButton(
            intensity_frame,
            text="Médio (CPU + RAM + Disco)",
            variable=self.collapse_intensity_var,
            value="medio",
            font=("Roboto", 12),
        ).grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkRadioButton(
            intensity_frame,
            text="Pesado (CPU + RAM + Disco + Rede)",
            variable=self.collapse_intensity_var,
            value="pesado",
            font=("Roboto", 12),
        ).grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Duração
        duration_frame = ctk.CTkFrame(collapse_frame, fg_color="transparent")
        duration_frame.pack(pady=10)

        ctk.CTkLabel(duration_frame, text="Duração (segundos, máx 300):", font=("Roboto", 14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.collapse_duration_entry = ctk.CTkEntry(duration_frame, width=100)
        self.collapse_duration_entry.insert(0, "30")
        self.collapse_duration_entry.grid(row=0, column=1, padx=10, pady=5)

        self.collapse_start_btn = ctk.CTkButton(
            collapse_frame,
            text="🔥 INICIAR COLAPSO 🔥",
            command=self.start_system_collapse,
            fg_color="#991b1b",
            hover_color="#7f1d1d",
            height=45,
            font=("Roboto", 15, "bold"),
            text_color="#fca5a5",
        )
        self.collapse_start_btn.pack(pady=(10, 15))

        # Card 3: Limpeza de Segurança
        cleanup_frame = ctk.CTkFrame(main_frame, fg_color="#1e3a5f", corner_radius=15)
        cleanup_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(
            cleanup_frame,
            text="🧹 Limpeza de Segurança",
            font=("Roboto", 20, "bold"),
        ).pack(pady=(15, 10))

        ctk.CTkLabel(
            cleanup_frame,
            text="Remove logs sensíveis e bloqueia o usuário atual",
            font=("Roboto", 12),
            text_color="#94a3b8",
        ).pack(pady=(0, 15))

        cleanup_btn_frame = ctk.CTkFrame(cleanup_frame, fg_color="transparent")
        cleanup_btn_frame.pack(pady=10)

        self.clean_logs_btn = ctk.CTkButton(
            cleanup_btn_frame,
            text="Limpar Logs Sensíveis",
            command=self.clean_logs,
            fg_color="#f59e0b",
            hover_color="#d97706",
            height=40,
            width=200,
            font=("Roboto", 14, "bold"),
        )
        self.clean_logs_btn.grid(row=0, column=0, padx=10, pady=5)

        self.lock_user_btn = ctk.CTkButton(
            cleanup_btn_frame,
            text="Bloquear Usuário Atual",
            command=self.lock_user,
            fg_color="#dc2626",
            hover_color="#991b1b",
            height=40,
            width=200,
            font=("Roboto", 14, "bold"),
        )
        self.lock_user_btn.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(cleanup_frame, text="", font=("Roboto", 10)).pack(pady=(0, 15))

    # ========== Funções de Emergência ==========

    def shutdown_now(self):
        """Desliga o sistema imediatamente."""
        shutdown_system()

    def schedule_shutdown(self):
        """Programa desligamento do sistema."""
        try:
            minutes = int(self.shutdown_minutes_entry.get())
            emergency_schedule_shutdown(minutes)
        except ValueError:
            pass

    def cancel_scheduled_shutdown(self):
        """Cancela desligamento programado."""
        emergency_cancel_scheduled_shutdown()

    def start_system_collapse(self):
        """Inicia colapso do sistema."""
        try:
            duration = float(self.collapse_duration_entry.get())
            intensity = self.collapse_intensity_var.get()
            
            # Limita duração a 300s
            if duration > 300:
                duration = 300.0

            self.collapse_start_btn.configure(state="disabled", text="⚠️ COLAPSO EM ANDAMENTO ⚠️")

            def collapse_thread():
                collapser = SystemCollapser()
                collapser.start_collapse(duration=duration, intensity=intensity)
                self.collapse_start_btn.configure(state="normal", text="🔥 INICIAR COLAPSO 🔥")

            threading.Thread(target=collapse_thread, daemon=True).start()

        except ValueError:
            pass

    def clean_logs(self):
        """Limpa logs sensíveis."""
        clean_sensitive_logs()

    def lock_user(self):
        """Bloqueia o usuário atual."""
        lock_current_user()

    # ========== Funções de Rede ==========

    def scan_network(self):
        """Escaneia a rede local e mostra os hosts ativos."""
        self.network_hosts_textbox.delete("1.0", "end")
        self.network_hosts_textbox.insert("1.0", "Escaneando rede...\n")
        self.scan_network_btn.configure(state="disabled", text="Escaneando...")

        def scan_thread():
            cidr = guess_local_network_cidr()
            if not cidr:
                self.safe_textbox_update(
                    self.network_hosts_textbox,
                    "1.0",
                    "Erro: Não foi possível determinar a faixa de rede local.\n"
                )
                self.scan_network_btn.configure(state="normal", text="Escanear Rede")
                return

            self.safe_textbox_update(
                self.network_hosts_textbox,
                "1.0",
                f"Escaneando {cidr}...\n\n"
            )

            hosts = scan_network_hosts(cidr)
            
            if not hosts:
                result = f"Nenhum host respondeu ao ping em {cidr}.\n"
            else:
                result = f"Hosts ativos em {cidr}:\n\n"
                for ip in hosts:
                    result += f"  • {ip}\n"

            self.safe_textbox_update(self.network_hosts_textbox, "1.0", result)
            self.scan_network_btn.configure(state="normal", text="Escanear Rede")

        threading.Thread(target=scan_thread, daemon=True).start()

    def scan_ports(self):
        """Escaneia portas comuns de um host."""
        ip = self.port_scan_ip_entry.get().strip()
        if not ip:
            self.port_scan_textbox.delete("1.0", "end")
            self.port_scan_textbox.insert("1.0", "Erro: Digite um IP válido.\n")
            return

        self.port_scan_textbox.delete("1.0", "end")
        self.port_scan_textbox.insert("1.0", f"Escaneando portas em {ip}...\n")
        self.port_scan_btn.configure(state="disabled", text="Escaneando...")

        def scan_thread():
            open_ports = scan_host_ports(ip)
            
            if not open_ports:
                result = f"Nenhuma porta comum aberta encontrada em {ip}.\n"
            else:
                result = f"Portas abertas em {ip}:\n\n"
                for port, desc in open_ports:
                    result += f"  • Porta {port:5d}  →  {desc or 'Desconhecido'}\n"

            self.safe_textbox_update(self.port_scan_textbox, "1.0", result)
            self.port_scan_btn.configure(state="disabled", text="Escanear Portas")

        threading.Thread(target=scan_thread, daemon=True).start()

    def show_netstat(self):
        """Mostra as conexões de rede locais."""
        self.netstat_textbox.delete("1.0", "end")
        self.netstat_textbox.insert("1.0", "Listando conexões...\n")
        self.netstat_btn.configure(state="disabled", text="Carregando...")

        def netstat_thread():
            conns = list_local_connections(limit=100)
            
            if not conns:
                result = "Nenhuma conexão encontrada ou acesso negado.\n"
            else:
                result = f"{'Proto':<6} {'Status':<15} {'Local':<25} {'Remoto':<25} {'PID':<8}\n"
                result += "=" * 85 + "\n"
                
                for c in conns:
                    proto = "TCP" if c["type"] == socket.SOCK_STREAM else "UDP"
                    result += f"{proto:<6} {c['status']:<15} {c['laddr']:<25} {c['raddr']:<25} {str(c['pid'] or '-'):<8}\n"

            self.safe_textbox_update(self.netstat_textbox, "1.0", result)
            self.netstat_btn.configure(state="normal", text="Ver Conexões")

        threading.Thread(target=netstat_thread, daemon=True).start()

    def analyze_network_security(self):
        """Analisa acessos remotos e anomalias de segurança de rede."""
        self.security_net_textbox.delete("1.0", "end")
        self.security_net_textbox.insert("1.0", "Analisando segurança de rede...\n\n")
        self.analyze_security_btn.configure(state="disabled", text="Analisando...")

        def analyze_thread():
            output = ""

            # 1) Sessões remotas ativas
            output += "═══ SESSÕES DE ACESSO REMOTO ATIVAS ═══\n\n"
            sessions = list_remote_access_sessions()
            if not sessions:
                output += "✓ Nenhuma sessão remota (SSH/RDP/VNC) detectada.\n\n"
            else:
                output += f"⚠ {len(sessions)} sessão(ões) remota(s) detectada(s):\n\n"
                for s in sessions:
                    output += f"  [{s.service}] {s.local_addr} ↔ {s.remote_addr}\n"
                    output += f"    Status: {s.status} | PID: {s.pid or 'N/D'} | Processo: {s.process_name or 'N/D'}\n\n"

            # 2) Picos de tráfego de rede
            output += "═══ PICOS DE TRÁFEGO DE REDE ═══\n\n"
            spike_events = check_network_spikes()
            if not spike_events:
                output += "✓ Nenhum pico anormal de tráfego detectado.\n\n"
            else:
                output += f"⚠ {len(spike_events)} pico(s) detectado(s):\n\n"
                for ev in spike_events:
                    output += f"  PICO de {ev.direction.upper()}:\n"
                    output += f"    Atual: {ev.current_kb_s:.1f} KB/s | Média: {ev.avg_kb_s:.1f} KB/s | Limiar: {ev.threshold_kb_s:.1f} KB/s\n\n"

            # 3) Tentativas de brute-force
            output += "═══ TENTATIVAS DE LOGIN ANÔMALAS ═══\n\n"

            # Heurística de conexões (Windows + Linux)
            brute_conns = detect_remote_login_bruteforce_from_conns(min_conns=10)
            if brute_conns:
                output += "⚠ Muitos acessos remotos do mesmo IP (heurística):\n\n"
                for ip, cnt in brute_conns.items():
                    output += f"  IP {ip} → {cnt} conexões recentes\n"
                output += "\n"

            # Logs SSH em Linux
            ssh_bruteforce = detect_ssh_bruteforce_linux(min_failures=5)
            if ssh_bruteforce:
                output += "⚠ Falhas de login SSH em logs (Linux):\n\n"
                for ip, cnt in ssh_bruteforce.items():
                    output += f"  IP {ip} → {cnt} falhas recentes\n"
                output += "\n"

            if not brute_conns and not ssh_bruteforce:
                output += "✓ Nenhuma anomalia forte de brute-force encontrada.\n\n"

            output += "═══ ANÁLISE CONCLUÍDA ═══\n"

            self.safe_textbox_update(self.security_net_textbox, "1.0", output)
            self.analyze_security_btn.configure(state="normal", text="Analisar Acessos Remotos e Anomalias")

        threading.Thread(target=analyze_thread, daemon=True).start()

    def open_rdp(self):
        """Abre conexão RDP."""
        ip = self.rdp_ip_entry.get().strip()
        if not ip:
            return

        if platform.system() == "Windows":
            os.system(f"start mstsc /v:{ip}")
        else:
            pass

    def open_ssh(self):
        """Abre conexão SSH."""
        ip = self.ssh_ip_entry.get().strip()
        user = self.ssh_user_entry.get().strip()
        if not ip or not user:
            return

        if platform.system() == "Windows":
            os.system(f'start cmd /k "ssh {user}@{ip}"')
        else:
            os.system(f'gnome-terminal -- ssh {user}@{ip}')

   # ========== ✅ FUNÇÃO DE RELATÓRIO FORENSE COMPLETO (APENAS TXT) ==========

    def generate_forensic_txt(self):
        """Gera relatório forense COMPLETO em TXT."""
        self.forensic_textbox.delete("1.0", "end")
        self.forensic_textbox.insert(
            "1.0",
            "Gerando relatório forense COMPLETO em TXT...\n\n"
            "Isso pode levar alguns segundos...\n",
        )
        
        # Desabilita botão
        self.forensic_txt_btn.configure(state="disabled", text="⏳ Gerando TXT...")

        def generate_thread():
            try:
                # Lê opções
                include_stress = self.include_stress_var.get()
                include_security = self.include_security_var.get()
                try:
                    stress_duration = int(self.stress_duration_entry.get())
                except:
                    stress_duration = 5

                # Gera TXT completo
                txt_path = generate_full_forensic_report(
                    output_dir="reports",
                    include_stress_tests=include_stress,
                    include_security_audit=include_security,
                    stress_duration=stress_duration
                )

                # Lê prévia do arquivo
                with open(txt_path, "r", encoding="utf-8") as f:
                    content = f.read()

                preview = content[:3000] + "\n\n[...]\n\n" if len(content) > 3000 else content
                preview += f"\n{'=' * 70}\n"
                preview += f"✓ Relatório TXT COMPLETO salvo com sucesso!\n"
                preview += f"📁 Arquivo: {txt_path}\n"
                preview += f"📊 Tamanho: {len(content)} caracteres\n"
                preview += f"\n💡 Dica: Abra o arquivo no Bloco de Notas ou VS Code para visualização completa.\n"

                self.safe_textbox_update(self.forensic_textbox, "1.0", preview)

            except Exception as e:
                error_msg = f"❌ Erro ao gerar relatório TXT:\n{str(e)}\n"
                self.safe_textbox_update(self.forensic_textbox, "1.0", error_msg)

            finally:
                self.forensic_txt_btn.configure(state="normal", text="📄 Gerar Relatório TXT Completo")

        threading.Thread(target=generate_thread, daemon=True).start()

    # ========== Funções auxiliares ==========

    def create_card(self, parent, title):
        """Cria um card estilizado."""
        frame = ctk.CTkFrame(parent, fg_color="#1e3a5f", corner_radius=15)
        frame.pack(padx=20, pady=10, fill="x")

        title_label = ctk.CTkLabel(
            frame,
            text=title,
            font=("Roboto", 18, "bold"),
        )
        title_label.pack(pady=(15, 10))

        content_label = ctk.CTkLabel(
            frame,
            text="Carregando...",
            font=("Consolas", 13),
            justify="left",
        )
        content_label.pack(padx=20, pady=(0, 15), anchor="w")

        return content_label

    def start_dashboard_updates(self):
        """Inicia a thread de atualização do dashboard."""
        def update_loop():
            while not self._is_closing:
                try:
                    snapshot = get_system_snapshot()
                    self.update_dashboard_display(snapshot)
                    time.sleep(2)
                except Exception as e:
                    print(f"Erro na atualização: {e}")
                    break

        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()

    def update_dashboard_display(self, snapshot):
        """Atualiza os cards do dashboard."""
        if self._is_closing:
            return

        try:
            # CPU & RAM
            cpu_text = ""
            for core in snapshot.cpu_ram.cores[:4]:  # Limita a 4 cores
                freq = f"{core.frequency_mhz:.0f}" if core.frequency_mhz else "N/D"
                temp = f"{core.temperature_c:.1f}" if core.temperature_c is not None else "N/D"
                cpu_text += f"Core {core.core_index}: {core.usage_percent:.1f}% | {freq} MHz | {temp}°C\n"
            
            cpu_text += f"\nRAM: {snapshot.cpu_ram.used_ram_gb:.2f} / {snapshot.cpu_ram.total_ram_gb:.2f} GB ({snapshot.cpu_ram.ram_usage_percent:.1f}%)"
            self.cpu_card.configure(text=cpu_text)

            # GPU
            if snapshot.gpus:
                gpu_text = ""
                for g in snapshot.gpus:
                    temp = f"{g.temperature_c:.1f}" if g.temperature_c is not None else "N/D"
                    gpu_text += f"{g.name}\nUso: {g.load_percent:.1f}% | Memória: {g.memory_used_mb:.0f}/{g.memory_total_mb:.0f} MB | Temp: {temp}°C\n"
                self.gpu_card.configure(text=gpu_text)
            else:
                self.gpu_card.configure(text="Nenhuma GPU detectada")

            # Discos
            if snapshot.disks:
                disk_text = ""
                for d in snapshot.disks[:3]:  # Limita a 3 discos
                    temp = f"{d.temperature_c:.1f}" if d.temperature_c is not None else "N/D"
                    disk_text += f"{d.device} ({d.mountpoint})\n"
                    disk_text += f"Uso: {d.used_gb:.1f}/{d.total_gb:.1f} GB | "
                    disk_text += f"R: {d.read_bytes_per_sec/1024:.1f} KB/s | W: {d.write_bytes_per_sec/1024:.1f} KB/s | Temp: {temp}°C\n\n"
                self.disk_card.configure(text=disk_text)
            else:
                self.disk_card.configure(text="Nenhum disco detectado")

            # Rede
            latency = f"{snapshot.network.latency_ms:.1f} ms" if snapshot.network.latency_ms is not None else "N/D"
            net_text = f"Download: {snapshot.network.bytes_recv_per_sec/1024:.1f} KB/s\n"
            net_text += f"Upload: {snapshot.network.bytes_sent_per_sec/1024:.1f} KB/s\n"
            net_text += f"Latência: {latency}"
            self.network_card.configure(text=net_text)

            # Bateria
            if snapshot.battery:
                b = snapshot.battery
                bat_text = f"Nível: {b.percent:.1f}%\n"
                bat_text += f"Status: {'Carregando' if b.power_plugged else 'Descarregando'}"
                if b.voltage_mV:
                    bat_text += f"\nTensão: {b.voltage_mV} mV"
                if b.current_mA:
                    bat_text += f"\nCorrente: {b.current_mA} mA"
                self.battery_card.configure(text=bat_text)
            else:
                self.battery_card.configure(text="Nenhuma bateria detectada")

        except Exception as e:
            print(f"Erro ao atualizar display: {e}")

    def run_cpu_stress(self):
        """Executa stress test de CPU."""
        try:
            threads = int(self.cpu_threads_entry.get())
            intensity = float(self.cpu_intensity_entry.get())
            duration = float(self.cpu_duration_entry.get())

            self.cpu_stress_btn.configure(state="disabled", text="Executando...")

            def stress_thread():
                start_cpu_stress(num_threads=threads, intensity=intensity, duration=duration)
                self.cpu_stress_btn.configure(state="normal", text="Iniciar Stress de CPU")

            threading.Thread(target=stress_thread, daemon=True).start()

        except ValueError:
            pass

    def run_ram_stress(self):
        """Executa stress test de RAM."""
        try:
            target_mb = int(self.ram_mb_entry.get())
            duration = float(self.ram_duration_entry.get())

            self.ram_stress_btn.configure(state="disabled", text="Executando...")

            def stress_thread():
                start_ram_stress(target_mb=target_mb, duration=duration)
                self.ram_stress_btn.configure(state="normal", text="Iniciar Stress de RAM")

            threading.Thread(target=stress_thread, daemon=True).start()

        except ValueError:
            pass

    def run_full_stress(self):
        """Executa stress test PESADO (CPU + RAM)."""
        try:
            duration = float(self.full_duration_entry.get())
            intensity = float(self.full_intensity_entry.get())

            # Limita duração a 600s
            if duration > 600:
                duration = 600.0

            self.full_stress_btn.configure(state="disabled", text="⚠️ EXECUTANDO STRESS PESADO ⚠️")

            def stress_thread():
                start_full_stress(duration=duration, cpu_intensity=intensity)
                self.full_stress_btn.configure(state="normal", text="🔥 INICIAR STRESS PESADO 🔥")

            threading.Thread(target=stress_thread, daemon=True).start()

        except ValueError:
            pass

    def run_security_scan(self):
        """Executa auditoria de segurança."""
        self.security_textbox.delete("1.0", "end")
        self.security_textbox.insert("1.0", "Executando varredura de segurança...\n\n")
        self.security_btn.configure(state="disabled", text="Executando...")

        def scan_thread():
            result = full_security_scan()
            overclock = result["overclock_tools"]
            net_anom = result["network_anomalies"]

            output = ""
            if not overclock and not net_anom:
                output = "✓ Nenhuma anomalia significativa detectada.\n"
            else:
                if overclock:
                    output += "⚠ Possíveis ferramentas de overclock/undervolt:\n\n"
                    for p in overclock:
                        output += f"  PID {p.pid} - {p.name}\n  Motivo: {p.reason}\n\n"

                if net_anom:
                    output += "\n⚠ Possíveis anomalias de rede:\n\n"
                    for p in net_anom:
                        output += f"  PID {p.pid} - {p.name}\n  Motivo: {p.reason}\n"
                        if p.extra_info:
                            output += f"  Info: {p.extra_info}\n"
                        output += "\n"

            self.safe_textbox_update(self.security_textbox, "1.0", output)
            self.security_btn.configure(state="normal", text="Executar Varredura")

        threading.Thread(target=scan_thread, daemon=True).start()

    def safe_textbox_update(self, textbox, position, text):
        """Atualiza textbox de forma segura (thread-safe)."""
        if self._is_closing:
            return
        try:
            textbox.delete("1.0", "end")
            textbox.insert(position, text)
        except Exception:
            pass

    def on_closing(self):
        """Fecha a aplicação de forma segura."""
        self._is_closing = True
        self.withdraw()
        time.sleep(0.3)
        self.quit()
        self.destroy()


def run_gui():
    """Função principal para rodar a GUI."""
    app = SystemMonitorGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
