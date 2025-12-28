# file: cli.py
"""
Interface de Linha de Comando (CLI) usando Rich para dashboard e comandos.

Funcionalidades:
- Dashboard em tempo real com:
    - CPU & RAM (por núcleo + total)
    - GPU(s)
    - Discos (I/O, espaço, temp)
    - Rede (up/down, latência)
    - Bateria (se houver)
- Menu simples para:
    - Iniciar stress de CPU
    - Iniciar stress de RAM
    - Iniciar stress PESADO (CPU + RAM combinado)
    - Rodar auditoria de segurança
    - Monitoramento de rede (scan de hosts, portas, conexões, RDP/SSH)
    - Análise de segurança de rede (sessões remotas, picos, brute-force)
    - Geração de relatório forense (máquina / rede / completo)
    - MÓDULO DE EMERGÊNCIA (Desligamento programado/remoto, colapso do sistema)

Este módulo foca na apresentação; a lógica de coleta está em hw_monitor.py,
e a de stress/auditoria em stress.py e security.py.
"""

import time
import socket
import os
import platform
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt, Confirm
from rich.text import Text

from config import REFRESH_INTERVAL_SECONDS
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
    schedule_shutdown,
    cancel_scheduled_shutdown,
    SystemCollapser,
    clean_sensitive_logs,
    lock_current_user,
    RemoteControlServer,
    EMERGENCY_PASSWORD_HASH,
)

from report import generate_forensic_report, generate_full_forensic_report


console = Console()


# ============================================================
# DASHBOARD EM TEMPO REAL
# ============================================================

def build_dashboard_layout() -> Layout:
    """
    Cria um layout Rich dividido em seções:
      - CPU & RAM
      - GPU
      - Discos
      - Rede
      - Bateria
    """
    layout = Layout()
    layout.split_column(
        Layout(name="cpu_ram", size=12),
        Layout(name="gpu", size=8),
        Layout(name="disks", size=10),
        Layout(name="network", size=5),
        Layout(name="battery", size=5),
    )
    return layout


def update_dashboard_layout(layout: Layout):
    """
    Atualiza o layout com dados do snapshot atual.
    """
    snapshot = get_system_snapshot()

    # ========== CPU & RAM ==========
    cpu_table = Table(title="CPU & RAM", show_header=True, header_style="bold cyan")
    cpu_table.add_column("Core", style="dim", width=6)
    cpu_table.add_column("Uso (%)", justify="right")
    cpu_table.add_column("Freq (MHz)", justify="right")
    cpu_table.add_column("Temp (°C)", justify="right")

    for core in snapshot.cpu_ram.cores:
        freq_str = f"{core.frequency_mhz:.0f}" if core.frequency_mhz else "N/D"
        temp_str = f"{core.temperature_c:.1f}" if core.temperature_c is not None else "N/D"
        cpu_table.add_row(
            f"Core {core.core_index}",
            f"{core.usage_percent:.1f}",
            freq_str,
            temp_str,
        )

    cpu_panel = Panel.fit(cpu_table, border_style="green")
    layout["cpu_ram"].update(cpu_panel)

    # ========== GPU ==========
    gpu_table = Table(title="GPU", show_header=True, header_style="bold magenta")
    gpu_table.add_column("Nome", style="cyan")
    gpu_table.add_column("Uso (%)", justify="right")
    gpu_table.add_column("Memória (MB)", justify="right")
    gpu_table.add_column("Temp (°C)", justify="right")

    if not snapshot.gpus:
        gpu_table.add_row("N/D", "N/D", "N/D", "N/D")
    else:
        for g in snapshot.gpus:
            temp_str = f"{g.temperature_c:.1f}" if g.temperature_c is not None else "N/D"
            gpu_table.add_row(
                g.name,
                f"{g.load_percent:.1f}",
                f"{g.memory_used_mb:.0f}/{g.memory_total_mb:.0f}",
                temp_str,
            )

    gpu_panel = Panel.fit(gpu_table, border_style="magenta")
    layout["gpu"].update(gpu_panel)

    # ========== Discos ==========
    disk_table = Table(title="Discos", show_header=True, header_style="bold blue")
    disk_table.add_column("Device", style="cyan")
    disk_table.add_column("Mount", style="dim")
    disk_table.add_column("Uso (GB)", justify="right")
    disk_table.add_column("I/O R (KB/s)", justify="right")
    disk_table.add_column("I/O W (KB/s)", justify="right")
    disk_table.add_column("Temp (°C)", justify="right")

    if not snapshot.disks:
        disk_table.add_row("N/D", "N/D", "N/D", "N/D", "N/D", "N/D")
    else:
        for d in snapshot.disks:
            temp_str = f"{d.temperature_c:.1f}" if d.temperature_c is not None else "N/D"
            disk_table.add_row(
                d.device,
                d.mountpoint,
                f"{d.used_gb:.1f}/{d.total_gb:.1f}",
                f"{d.read_bytes_per_sec / 1024:.1f}",
                f"{d.write_bytes_per_sec / 1024:.1f}",
                temp_str,
            )

    disk_panel = Panel.fit(disk_table, border_style="blue")
    layout["disks"].update(disk_panel)

    # ========== Rede ==========
    latency_str = (
        f"{snapshot.network.latency_ms:.1f} ms"
        if snapshot.network.latency_ms is not None
        else "N/D"
    )
    net_text = Text()
    net_text.append(
        f"Download: {snapshot.network.bytes_recv_per_sec / 1024:.1f} KB/s | "
        f"Upload: {snapshot.network.bytes_sent_per_sec / 1024:.1f} KB/s | "
        f"Latência: {latency_str}",
        style="bold green",
    )
    net_panel = Panel.fit(net_text, title="Rede", border_style="green")
    layout["network"].update(net_panel)

    # ========== Bateria ==========
    if snapshot.battery:
        b = snapshot.battery
        bat_text = Text()
        bat_text.append(
            f"Nível: {b.percent:.1f}% | "
            f"Status: {'Carregando' if b.power_plugged else 'Descarregando'}",
            style="bold yellow",
        )
        if b.voltage_mV is not None:
            bat_text.append(f" | Tensão: {b.voltage_mV} mV")
        if b.current_mA is not None:
            bat_text.append(f" | Corrente: {b.current_mA} mA")
    else:
        bat_text = Text("Nenhuma bateria detectada.", style="dim")

    bat_panel = Panel.fit(bat_text, title="Bateria", border_style="yellow")
    layout["battery"].update(bat_panel)


def dashboard_realtime(duration: Optional[float] = None):
    """
    Exibe o dashboard em tempo real usando Rich Live.
    Se duration for None, roda indefinidamente até Ctrl+C.
    """
    layout = build_dashboard_layout()

    start_time = time.time()
    try:
        with Live(layout, console=console, refresh_per_second=2):
            while True:
                update_dashboard_layout(layout)
                time.sleep(REFRESH_INTERVAL_SECONDS)

                if duration is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= duration:
                        break
    except KeyboardInterrupt:
        console.print("\n[red]Dashboard interrompido pelo usuário.[/red]")


# ============================================================
# STRESS TEST
# ============================================================

def stress_cpu_menu():
    """
    Menu interativo para stress de CPU.
    """
    console.print("\n[bold cyan]===== Stress Test de CPU =====[/bold cyan]")
    threads = IntPrompt.ask("Número de threads", default=4)
    intensity = float(Prompt.ask("Intensidade (0.1 a 1.0)", default="1.0"))
    duration = float(Prompt.ask("Duração (segundos)", default="30"))

    console.print(
        f"\n[yellow]Iniciando stress de CPU: {threads} threads, intensidade {intensity}, por {duration}s...[/yellow]"
    )
    start_cpu_stress(num_threads=threads, intensity=intensity, duration=duration)
    console.print("[green]Stress de CPU finalizado.[/green]")


def stress_ram_menu():
    """
    Menu interativo para stress de RAM.
    """
    console.print("\n[bold cyan]===== Stress Test de RAM =====[/bold cyan]")
    target_mb = IntPrompt.ask("Memória a alocar (MB)", default=512)
    duration = float(Prompt.ask("Duração (segundos)", default="30"))

    console.print(
        f"\n[yellow]Iniciando stress de RAM: {target_mb} MB por {duration}s...[/yellow]"
    )
    start_ram_stress(target_mb=target_mb, duration=duration)
    console.print("[green]Stress de RAM finalizado.[/green]")


def stress_full_menu():
    """
    Menu interativo para stress PESADO (CPU + RAM combinado).
    """
    console.print("\n[bold red]===== ⚠️  STRESS PESADO (CPU + RAM) ⚠️  =====[/bold red]")
    console.print("[yellow]ATENÇÃO: Este modo usa TODOS os núcleos da CPU e aloca ~60% da RAM.[/yellow]")
    console.print("[yellow]Pode deixar o sistema MUITO lento durante o teste.[/yellow]")
    console.print("[yellow]Certifique-se de salvar todos os arquivos abertos antes de continuar.[/yellow]\n")

    confirm = Prompt.ask("Deseja continuar? (s/n)", default="n")
    if confirm.lower() not in ["s", "sim", "y", "yes"]:
        console.print("[red]Operação cancelada.[/red]")
        return

    duration = float(Prompt.ask("Duração (segundos, máx 600)", default="60"))
    if duration > 600:
        duration = 600.0
        console.print("[yellow]Duração limitada a 600s (10 minutos).[/yellow]")

    intensity = float(Prompt.ask("Intensidade da CPU (0.1 a 1.0)", default="1.0"))

    console.print(
        f"\n[bold red]Iniciando STRESS PESADO por {duration:.0f}s...[/bold red]"
    )
    console.print("[yellow]Pressione Ctrl+C para interromper (não recomendado).[/yellow]\n")

    try:
        start_full_stress(duration=duration, cpu_intensity=intensity)
        console.print("[green]Stress pesado finalizado com sucesso.[/green]")
    except KeyboardInterrupt:
        console.print("\n[red]Stress interrompido pelo usuário.[/red]")


# ============================================================
# SEGURANÇA (AUDITORIA E REDE)
# ============================================================

def security_audit_menu():
    """
    Menu interativo para auditoria de segurança.
    """
    console.print("\n[bold cyan]===== Auditoria de Segurança =====[/bold cyan]")
    console.print("[yellow]Executando varredura...[/yellow]\n")

    result = full_security_scan()
    overclock = result["overclock_tools"]
    net_anom = result["network_anomalies"]

    if not overclock and not net_anom:
        console.print("[green]✓ Nenhuma anomalia significativa detectada.[/green]")
    else:
        if overclock:
            console.print("[bold red]⚠ Possíveis ferramentas de overclock/undervolt:[/bold red]")
            for p in overclock:
                console.print(f"  PID {p.pid} - {p.name} - {p.reason}")

        if net_anom:
            console.print("\n[bold red]⚠ Possíveis anomalias de rede:[/bold red]")
            for p in net_anom:
                console.print(
                    f"  PID {p.pid} - {p.name} - {p.reason} - {p.extra_info or '-'}"
                )


def network_security_analysis_menu():
    """
    Análise de segurança de rede:
    - Sessões de acesso remoto ativas (SSH/RDP/VNC)
    - Picos anormais de tráfego de rede
    - Detecção de brute-force (logs Linux + heurística de conexões)
    """
    console.print("\n[bold cyan]===== 🔒 Análise de Segurança de Rede =====[/bold cyan]\n")
    console.print("[yellow]Analisando acessos remotos e anomalias...[/yellow]\n")

    # 1) Sessões remotas ativas
    console.print("[bold magenta]═══ SESSÕES DE ACESSO REMOTO ATIVAS ═══[/bold magenta]\n")
    sessions = list_remote_access_sessions()
    if not sessions:
        console.print("[green]✓ Nenhuma sessão remota (SSH/RDP/VNC) detectada.[/green]\n")
    else:
        console.print(f"[bold red]⚠ {len(sessions)} sessão(ões) remota(s) detectada(s):[/bold red]\n")
        table = Table(show_header=True, header_style="bold red")
        table.add_column("Serviço", style="cyan")
        table.add_column("Local", style="yellow")
        table.add_column("Remoto", style="yellow")
        table.add_column("Status", style="dim")
        table.add_column("PID", justify="right")
        table.add_column("Processo", style="dim")

        for s in sessions:
            table.add_row(
                s.service,
                s.local_addr,
                s.remote_addr,
                s.status,
                str(s.pid or "N/D"),
                s.process_name or "N/D",
            )
        console.print(table)
        console.print()

    # 2) Picos de tráfego de rede
    console.print("[bold magenta]═══ PICOS DE TRÁFEGO DE REDE ═══[/bold magenta]\n")
    spike_events = check_network_spikes()
    if not spike_events:
        console.print("[green]✓ Nenhum pico anormal de tráfego detectado.[/green]\n")
    else:
        console.print(f"[bold red]⚠ {len(spike_events)} pico(s) detectado(s):[/bold red]\n")
        for ev in spike_events:
            console.print(f"  [red]PICO de {ev.direction.upper()}:[/red]")
            console.print(
                f"    Atual: {ev.current_kb_s:.1f} KB/s | "
                f"Média: {ev.avg_kb_s:.1f} KB/s | "
                f"Limiar: {ev.threshold_kb_s:.1f} KB/s\n"
            )

    # 3) Tentativas de brute-force
    console.print("[bold magenta]═══ TENTATIVAS DE LOGIN ANÔMALAS ═══[/bold magenta]\n")

    # Heurística de conexões (Windows + Linux)
    brute_conns = detect_remote_login_bruteforce_from_conns(min_conns=10)
    if brute_conns:
        console.print("[bold red]⚠ Muitos acessos remotos do mesmo IP (heurística):[/bold red]\n")
        table = Table(show_header=True, header_style="bold red")
        table.add_column("IP Remoto", style="yellow")
        table.add_column("Conexões Recentes", justify="right", style="red")
        for ip, cnt in brute_conns.items():
            table.add_row(ip, str(cnt))
        console.print(table)
        console.print()

    # Logs SSH em Linux
    ssh_bruteforce = detect_ssh_bruteforce_linux(min_failures=5)
    if ssh_bruteforce:
        console.print("[bold red]⚠ Falhas de login SSH em logs (Linux):[/bold red]\n")
        table = Table(show_header=True, header_style="bold red")
        table.add_column("IP Remoto", style="yellow")
        table.add_column("Falhas Recentes", justify="right", style="red")
        for ip, cnt in ssh_bruteforce.items():
            table.add_row(ip, str(cnt))
        console.print(table)
        console.print()

    if not brute_conns and not ssh_bruteforce:
        console.print("[green]✓ Nenhuma anomalia forte de brute-force encontrada.[/green]\n")

    console.print("[bold magenta]═══ ANÁLISE CONCLUÍDA ═══[/bold magenta]\n")


# ============================================================
# FUNÇÕES AUXILIARES DE REDE
# ============================================================

def open_rdp(ip: str):
    """
    Abre conexão RDP para o IP especificado (Windows apenas).
    """
    if platform.system() == "Windows":
        console.print(f"[green]Abrindo RDP para {ip}...[/green]")
        os.system(f"start mstsc /v:{ip}")
    else:
        console.print("[red]RDP automático só implementado para Windows.[/red]")


def open_ssh(ip: str, user: str = "root"):
    """
    Abre conexão SSH para o IP especificado.
    """
    console.print(f"[green]Abrindo SSH para {user}@{ip}...[/green]")
    if platform.system() == "Windows":
        os.system(f'start cmd /k "ssh {user}@{ip}"')
    else:
        os.system(f'gnome-terminal -- ssh {user}@{ip}')


def network_monitor_menu():
    """
    Menu de monitoramento de rede:
    - Descobrir hosts na rede local
    - Ver portas abertas em um host
    - Ver conexões locais (netstat)
    - Acesso remoto (RDP/SSH)
    - Análise de segurança de rede
    """
    while True:
        console.print("\n[bold cyan]===== Monitoramento de Rede =====[/bold cyan]")
        console.print("[cyan]1)[/cyan] Descobrir hosts na rede local")
        console.print("[cyan]2)[/cyan] Ver portas comuns em um host")
        console.print("[cyan]3)[/cyan] Ver conexões locais (tipo netstat)")
        console.print("[cyan]4)[/cyan] Abrir RDP para um host")
        console.print("[cyan]5)[/cyan] Abrir SSH para um host")
        console.print("[cyan]6)[/cyan] 🔒 Análise de Segurança de Rede (Sessões Remotas + Anomalias)")
        console.print("[cyan]0)[/cyan] Voltar\n")

        try:
            choice = IntPrompt.ask("Opção", default=1)
        except KeyboardInterrupt:
            console.print("\n[red]Voltando ao menu principal...[/red]")
            return

        if choice == 1:
            cidr = guess_local_network_cidr()
            if not cidr:
                console.print("[red]Não foi possível determinar a faixa de rede local.[/red]")
                continue

            console.print(f"[yellow]Escaneando rede {cidr}... (ping sweep básico)[/yellow]")
            hosts = scan_network_hosts(cidr)
            if not hosts:
                console.print("[red]Nenhum host respondeu ao ping.[/red]")
            else:
                table = Table(title=f"Hosts ativos em {cidr}", show_header=True, header_style="bold green")
                table.add_column("IP")
                for ip in hosts:
                    table.add_row(ip)
                console.print(table)

        elif choice == 2:
            ip = Prompt.ask("IP do host", default="192.168.0.1")
            console.print(f"[yellow]Escaneando portas comuns em {ip}...[/yellow]")
            open_ports = scan_host_ports(ip)
            if not open_ports:
                console.print("[red]Nenhuma porta comum aberta encontrada.[/red]")
            else:
                table = Table(title=f"Portas abertas em {ip}", show_header=True, header_style="bold magenta")
                table.add_column("Porta", justify="right")
                table.add_column("Serviço", justify="left")
                for port, desc in open_ports:
                    table.add_row(str(port), desc or "-")
                console.print(table)

        elif choice == 3:
            console.print("[yellow]Listando conexões locais (limitado)...[/yellow]")
            conns = list_local_connections(limit=80)
            if not conns:
                console.print("[red]Nenhuma conexão encontrada ou acesso negado.[/red]")
            else:
                table = Table(title="Conexões locais", show_header=True, header_style="bold blue")
                table.add_column("Proto", justify="left")
                table.add_column("Status", justify="left")
                table.add_column("Local", justify="left")
                table.add_column("Remoto", justify="left")
                table.add_column("PID", justify="right")

                for c in conns:
                    proto = "TCP" if c["type"] == socket.SOCK_STREAM else "UDP"
                    table.add_row(
                        proto,
                        c["status"],
                        c["laddr"],
                        c["raddr"],
                        str(c["pid"] or "-"),
                    )
                console.print(table)

        elif choice == 4:
            ip = Prompt.ask("IP do host para RDP", default="192.168.0.1")
            open_rdp(ip)

        elif choice == 5:
            ip = Prompt.ask("IP do host para SSH", default="192.168.0.1")
            user = Prompt.ask("Usuário SSH", default="root")
            open_ssh(ip, user)

        elif choice == 6:
            network_security_analysis_menu()

        elif choice == 0:
            return

        else:
            console.print("[red]Opção inválida. Tente novamente.[/red]")


# ============================================================
# RELATÓRIO FORENSE (usando report.py)
# ============================================================

def forensic_report_menu():
    """
    Menu para geração de relatório forense em formato TXT.
    """
    console.print("\n[bold cyan]===== 📄 Relatório Forense (TXT) =====[/bold cyan]")
    console.print("[yellow]Gerando relatório completo...[/yellow]\n")

    try:
        # Chama a função que gera o TXT (ajuste o nome se for diferente no seu código)
        # Geralmente essa função retorna o caminho do arquivo gerado
        filepath = generate_full_forensic_report(output_dir="reports") 
        
        console.print("[green]✓ Relatório TXT gerado com sucesso![/green]")
        console.print(f"[bold]Localização:[/bold] {filepath}")
        console.print("[dim]Dica: Você pode abrir este arquivo no Bloco de Notas ou VS Code.[/dim]\n")
    except Exception as e:
        console.print(f"[red]Erro ao gerar relatório: {e}[/red]")

# ============================================================
# MÓDULO DE EMERGÊNCIA
# ============================================================

def emergency_shutdown_menu():
    """
    Menu para desligamento do sistema.
    """
    console.print("\n[bold red]===== ⚠️  DESLIGAMENTO DO SISTEMA ⚠️  =====[/bold red]")
    console.print("[yellow]ATENÇÃO: Esta operação desligará o computador![/yellow]")
    console.print("[yellow]Certifique-se de salvar todos os trabalhos antes de continuar.[/yellow]\n")
    
    console.print("[cyan]1)[/cyan] Desligar agora")
    console.print("[cyan]2)[/cyan] Desligar com atraso (programado)")
    console.print("[cyan]3)[/cyan] Cancelar desligamento programado")
    console.print("[cyan]0)[/cyan] Voltar\n")
    
    try:
        choice = IntPrompt.ask("Opção", default=0)
    except KeyboardInterrupt:
        console.print("\n[red]Operação cancelada.[/red]")
        return
    
    if choice == 1:
        confirm = Confirm.ask("[bold red]Tem certeza que deseja desligar o sistema agora?[/bold red]")
        if confirm:
            console.print("[yellow]Desligando o sistema em 5 segundos...[/yellow]")
            time.sleep(5)
            shutdown_system()
        else:
            console.print("[green]Operação cancelada.[/green]")
    
    elif choice == 2:
        minutes = IntPrompt.ask("Minutos até o desligamento", default=10)
        if minutes <= 0:
            console.print("[red]O tempo deve ser maior que 0 minutos.[/red]")
            return
        
        confirm = Confirm.ask(f"[bold red]Desligar o sistema em {minutes} minutos?[/bold red]")
        if confirm:
            schedule_shutdown(minutes)
            console.print(f"[green]Desligamento programado para daqui a {minutes} minutos.[/green]")
            console.print(f"[yellow]Use a opção 3 para cancelar.[/yellow]")
        else:
            console.print("[green]Operação cancelada.[/green]")
    
    elif choice == 3:
        if cancel_scheduled_shutdown():
            console.print("[green]Desligamento programado cancelado.[/green]")
        else:
            console.print("[yellow]Nenhum desligamento programado encontrado.[/yellow]")
    
    elif choice == 0:
        return
    
    else:
        console.print("[red]Opção inválida.[/red]")


def system_collapse_menu():
    """
    Menu para colapso do sistema (teste de estabilidade extremo).
    """
    console.print("\n[bold red]===== ⚠️  COLAPSO DO SISTEMA ⚠️  =====[/bold red]")
    console.print("[yellow]ATENÇÃO: Esta operação pode travar ou reiniciar o sistema![/yellow]")
    console.print("[yellow]Use apenas para testes de estabilidade em ambientes controlados.[/yellow]")
    console.print("[yellow]Salve todos os trabalhos antes de continuar.[/yellow]\n")
    
    confirm = Confirm.ask("[bold red]Deseja realmente iniciar o colapso do sistema?[/bold red]")
    if not confirm:
        console.print("[green]Operação cancelada.[/green]")
        return
    
    duration = IntPrompt.ask("Duração em segundos (máx 300)", default=30)
    if duration > 300:
        duration = 300
        console.print("[yellow]Duração limitada a 300 segundos.[/yellow]")
    
    console.print(f"\n[bold red]Iniciando colapso do sistema por {duration} segundos...[/bold red]")
    console.print("[yellow]O sistema ficará extremamente lento![/yellow]\n")
    
    try:
        collapser = SystemCollapser()
        collapser.start_full_collapse(duration_seconds=duration)
        console.print("[green]Colapso finalizado.[/green]")
    except KeyboardInterrupt:
        console.print("\n[red]Colapso interrompido pelo usuário.[/red]")
        collapser.stop_collapse()
    except Exception as e:
        console.print(f"[red]Erro durante o colapso: {e}[/red]")


def security_cleanup_menu():
    """
    Menu para limpeza de segurança.
    """
    console.print("\n[bold cyan]===== 🔒 LIMPEZA DE SEGURANÇA =====[/bold cyan]")
    console.print("[yellow]ATENÇÃO: Algumas operações podem afetar logs do sistema.[/yellow]\n")
    
    console.print("[cyan]1)[/cyan] Limpar logs sensíveis do sistema")
    console.print("[cyan]2)[/cyan] Bloquear sessão do usuário atual")
    console.print("[cyan]0)[/cyan] Voltar\n")
    
    try:
        choice = IntPrompt.ask("Opção", default=0)
    except KeyboardInterrupt:
        console.print("\n[red]Operação cancelada.[/red]")
        return
    
    if choice == 1:
        confirm = Confirm.ask("[bold red]Limpar logs sensíveis do sistema?[/bold red]")
        if confirm:
            console.print("[yellow]Limpando logs...[/yellow]")
            count = clean_sensitive_logs()
            console.print(f"[green]Limpeza concluída. {count} arquivos removidos.[/green]")
        else:
            console.print("[green]Operação cancelada.[/green]")
    
    elif choice == 2:
        confirm = Confirm.ask("[bold red]Bloquear a sessão do usuário atual?[/bold red]")
        if confirm:
            console.print("[yellow]Bloqueando sessão...[/yellow]")
            lock_current_user()
            console.print("[green]Sessão bloqueada.[/green]")
        else:
            console.print("[green]Operação cancelada.[/green]")
    
    elif choice == 0:
        return
    
    else:
        console.print("[red]Opção inválida.[/red]")


def remote_control_menu():
    """
    Menu para controle remoto via rede.
    """
    console.print("\n[bold cyan]===== 🌐 CONTROLE REMOTO VIA REDE =====[/bold cyan]")
    console.print("[yellow]ATENÇÃO: Esta função inicia um servidor que pode receber comandos remotos.[/yellow]")
    console.print("[yellow]Use apenas em redes confiáveis e com autenticação adequada.[/yellow]\n")
    
    port = IntPrompt.ask("Porta do servidor", default=8080)
    
    console.print(f"\n[yellow]Iniciando servidor na porta {port}...[/yellow]")
    console.print("[yellow]Pressione Ctrl+C para parar o servidor.[/yellow]\n")
    
    try:
        remote_server = RemoteControlServer(port=port, password_hash=EMERGENCY_PASSWORD_HASH)
        if remote_server.start():
            console.print("[green]Servidor iniciado com sucesso![/green]")
            console.print(f"[bold]Comandos disponíveis:[/bold]")
            console.print(f"  - Status  : http://IP:{port}/?cmd=status&auth=HASH")
            console.print(f"  - Shutdown: http://IP:{port}/?cmd=shutdown&auth=HASH")
            console.print(f"  - Cancel  : http://IP:{port}/?cmd=cancel&auth=HASH\n")
            
            # Manter servidor rodando
            while remote_server.running:
                time.sleep(1)
        else:
            console.print("[red]Falha ao iniciar servidor.[/red]")
    except KeyboardInterrupt:
        console.print("\n[red]Servidor interrompido pelo usuário.[/red]")
        if remote_server:
            remote_server.stop()
    except Exception as e:
        console.print(f"[red]Erro ao iniciar servidor: {e}[/red]")


def emergency_module_menu():
    """
    Menu principal do módulo de emergência.
    """
    while True:
        console.print("\n[bold red]===== ⚠️  MÓDULO DE EMERGÊNCIA ⚠️  =====[/bold red]")
        console.print("[bold red]ATENÇÃO: Estas funções podem causar perda de dados ou travamento![/bold red]\n")
        
        console.print("[cyan]1)[/cyan] ⚡ Desligamento do Sistema")
        console.print("[cyan]2)[/cyan] 💥 Colapso do Sistema (Teste de Estabilidade)")
        console.print("[cyan]3)[/cyan] 🔒 Limpeza de Segurança")
        console.print("[cyan]4)[/cyan] 🌐 Controle Remoto via Rede")
        console.print("[cyan]0)[/cyan] Voltar ao Menu Principal\n")
        
        try:
            choice = IntPrompt.ask("Opção", default=0)
        except KeyboardInterrupt:
            console.print("\n[red]Voltando ao menu principal...[/red]")
            return
        
        if choice == 1:
            emergency_shutdown_menu()
        elif choice == 2:
            system_collapse_menu()
        elif choice == 3:
            security_cleanup_menu()
        elif choice == 4:
            remote_control_menu()
        elif choice == 0:
            return
        else:
            console.print("[red]Opção inválida. Tente novamente.[/red]")


# ============================================================
# MENU PRINCIPAL
# ============================================================

def main_menu():
    """
    Menu principal da CLI.
    """
    console.print("\n[bold green]===== System Monitor - CLI =====[/bold green]\n")

    while True:
        console.print("[bold cyan]1)[/bold cyan] Dashboard em tempo real")
        console.print("[bold cyan]2)[/bold cyan] Stress Test (CPU/RAM/Pesado)")
        console.print("[bold cyan]3)[/bold cyan] Auditoria de Segurança")
        console.print("[bold cyan]4)[/bold cyan] Monitoramento de Rede")
        console.print("[bold cyan]5)[/bold cyan] 📄 Gerar Relatório Forense")
        console.print("[bold red]6)[/bold red] ⚠️  Módulo de Emergência")
        console.print("[bold cyan]0)[/bold cyan] Sair\n")

        try:
            choice = IntPrompt.ask("Opção", default=1)
        except KeyboardInterrupt:
            console.print("\n[red]Interrompido pelo usuário. Saindo...[/red]")
            break

        if choice == 1:
            console.print("\n[yellow]Pressione Ctrl+C para voltar ao menu.[/yellow]\n")
            dashboard_realtime()

        elif choice == 2:
            console.print("\n[bold cyan]===== Stress Test =====[/bold cyan]")
            console.print("[cyan]1)[/cyan] Stress de CPU")
            console.print("[cyan]2)[/cyan] Stress de RAM")
            console.print("[bold red]3)[/bold red] ⚠️  Stress PESADO (CPU + RAM)")
            console.print("[cyan]0)[/cyan] Voltar\n")

            try:
                sub_choice = IntPrompt.ask("Opção", default=1)
            except KeyboardInterrupt:
                console.print("\n[red]Voltando ao menu principal...[/red]")
                continue

            if sub_choice == 1:
                stress_cpu_menu()
            elif sub_choice == 2:
                stress_ram_menu()
            elif sub_choice == 3:
                stress_full_menu()

        elif choice == 3:
            security_audit_menu()

        elif choice == 4:
            network_monitor_menu()

        elif choice == 5:
            forensic_report_menu()

        elif choice == 6:
            emergency_module_menu()

        elif choice == 0:
            console.print("\n[green]Encerrando System Monitor. Até logo![/green]")
            break

        else:
            console.print("[red]Opção inválida. Tente novamente.[/red]")


if __name__ == "__main__":
    main_menu()