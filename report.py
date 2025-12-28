# report.py
"""
Módulo de geração de relatórios forenses COMPLETOS do System Monitor.
Gera relatório textual (.txt) com TODAS as informações: sistema, hardware, rede, stress tests, segurança
"""

import os
import socket
import platform
from datetime import datetime
from typing import Optional, Dict, List, Any

import psutil

# Importa os módulos do seu projeto (ajuste os nomes se necessário)
try:
    from hw_monitor import get_battery_info, get_gpu_info
    from stress import stress_cpu, stress_ram
    from security import (
        audit_processes,
        detect_overclocking_tools,
        detect_network_anomalies
    )
except ImportError:
    # Fallback caso os módulos não estejam disponíveis
    get_battery_info = None
    get_gpu_info = None
    stress_cpu = None
    stress_ram = None
    audit_processes = None
    detect_overclocking_tools = None
    detect_network_anomalies = None


# ============================================================================
# FUNÇÕES DE COLETA DE DADOS
# ============================================================================

def get_basic_system_info():
    uname = platform.uname()
    hostname = socket.gethostname()
    try:
        ip_addr = socket.gethostbyname(hostname)
    except Exception:
        ip_addr = "N/D"

    return {
        "hostname": hostname,
        "ip": ip_addr,
        "system": uname.system,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor or "N/D",
    }


def get_cpu_info_snapshot():
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False) or cpu_count_logical
    try:
        freq = psutil.cpu_freq()
        freq_current = freq.current if freq else None
        freq_max = freq.max if freq else None
    except:
        freq_current = None
        freq_max = None
    
    return {
        "percent": cpu_percent,
        "logical": cpu_count_logical,
        "physical": cpu_count_physical,
        "freq_current": freq_current,
        "freq_max": freq_max,
    }


def get_ram_info_snapshot():
    vm = psutil.virtual_memory()
    return {
        "total": vm.total,
        "available": vm.available,
        "used": vm.used,
        "percent": vm.percent,
    }


def get_disk_info_snapshot():
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except PermissionError:
            continue
    return disks


def get_net_info_snapshot():
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    counters = psutil.net_io_counters(pernic=True)

    interfaces = []
    for name, addr_list in addrs.items():
        iface = {
            "name": name,
            "isup": stats.get(name).isup if name in stats else None,
            "addresses": [],
            "bytes_sent": counters.get(name).bytes_sent if name in counters else None,
            "bytes_recv": counters.get(name).bytes_recv if name in counters else None,
        }
        for addr in addr_list:
            iface["addresses"].append({
                "family": str(addr.family),
                "address": addr.address,
                "netmask": addr.netmask,
                "broadcast": getattr(addr, "broadcast", None),
            })
        interfaces.append(iface)

    return interfaces


def get_battery_snapshot():
    """Coleta informações da bateria (se disponível)"""
    if get_battery_info is None:
        return None
    try:
        return get_battery_info()
    except:
        return None


def get_gpu_snapshot():
    """Coleta informações da GPU (se disponível)"""
    if get_gpu_info is None:
        return None
    try:
        return get_gpu_info()
    except:
        return None


def get_stress_test_results(test_type: str = "cpu", duration: int = 5) -> Dict[str, Any]:
    """
    Executa um stress test e retorna os resultados.
    test_type: "cpu" ou "ram"
    duration: duração em segundos
    """
    if test_type == "cpu" and stress_cpu:
        try:
            return stress_cpu(duration=duration)
        except:
            return {"error": "Falha ao executar stress test de CPU"}
    elif test_type == "ram" and stress_ram:
        try:
            return stress_ram(duration=duration)
        except:
            return {"error": "Falha ao executar stress test de RAM"}
    else:
        return {"error": f"Stress test '{test_type}' não disponível"}


def get_security_audit() -> Dict[str, Any]:
    """Executa auditoria de segurança completa"""
    results = {}
    
    if audit_processes:
        try:
            results["processes"] = audit_processes()
        except:
            results["processes"] = {"error": "Falha na auditoria de processos"}
    
    if detect_overclocking_tools:
        try:
            results["overclocking"] = detect_overclocking_tools()
        except:
            results["overclocking"] = {"error": "Falha na detecção de overclock"}
    
    if detect_network_anomalies:
        try:
            results["network_anomalies"] = detect_network_anomalies()
        except:
            results["network_anomalies"] = {"error": "Falha na detecção de anomalias de rede"}
    
    return results


def bytes_to_human(n):
    if n is None:
        return "N/D"
    symbols = ("B", "KB", "MB", "GB", "TB")
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (10 * i)

    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return f"{value:.2f} {s}"
    return f"{n} B"


# ============================================================================
# GERAÇÃO DO RELATÓRIO TXT COMPLETO
# ============================================================================

def generate_full_forensic_report(
    output_dir: str = "reports",
    include_stress_tests: bool = True,
    include_security_audit: bool = True,
    stress_duration: int = 5
) -> str:
    """
    Gera um relatório forense COMPLETO em formato .txt
    
    Parâmetros:
    - output_dir: diretório de saída
    - include_stress_tests: incluir testes de stress (CPU e RAM)
    - include_security_audit: incluir auditoria de segurança
    - stress_duration: duração dos stress tests em segundos
    """
    os.makedirs(output_dir, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"relatorio_completo_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    # Coleta TODOS os dados
    sysinfo = get_basic_system_info()
    cpu = get_cpu_info_snapshot()
    ram = get_ram_info_snapshot()
    disks = get_disk_info_snapshot()
    nets = get_net_info_snapshot()
    battery = get_battery_snapshot()
    gpu = get_gpu_snapshot()
    
    stress_cpu_results = None
    stress_ram_results = None
    if include_stress_tests:
        stress_cpu_results = get_stress_test_results("cpu", stress_duration)
        stress_ram_results = get_stress_test_results("ram", stress_duration)
    
    security = None
    if include_security_audit:
        security = get_security_audit()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("RELATÓRIO FORENSE COMPLETO - SYSTEM MONITOR\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Data/Hora de geração: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Hostname: {sysinfo['hostname']}\n")
        f.write(f"Endereço IP: {sysinfo['ip']}\n")
        f.write(f"Sistema: {sysinfo['system']} ({sysinfo['release']})\n")
        f.write(f"Arquitetura: {sysinfo['machine']}\n")
        f.write(f"Processador: {sysinfo['processor']}\n")
        f.write("\n")

        # SEÇÃO 1: HARDWARE
        f.write("-" * 80 + "\n")
        f.write("SEÇÃO 1 - ESTADO ATUAL DO HARDWARE\n")
        f.write("-" * 80 + "\n\n")

        f.write("[CPU]\n")
        f.write(f"  Núcleos físicos : {cpu['physical']}\n")
        f.write(f"  Núcleos lógicos : {cpu['logical']}\n")
        f.write(f"  Uso atual       : {cpu['percent']:.1f}%\n")
        if cpu['freq_current']:
            f.write(f"  Frequência atual: {cpu['freq_current']:.0f} MHz\n")
        if cpu['freq_max']:
            f.write(f"  Frequência máxima: {cpu['freq_max']:.0f} MHz\n")
        f.write("\n")

        f.write("[MEMÓRIA RAM]\n")
        f.write(f"  Total     : {bytes_to_human(ram['total'])}\n")
        f.write(f"  Usada     : {bytes_to_human(ram['used'])} ({ram['percent']:.1f}%)\n")
        f.write(f"  Disponível: {bytes_to_human(ram['available'])}\n\n")

        if gpu:
            f.write("[GPU]\n")
            if isinstance(gpu, list):
                for i, g in enumerate(gpu):
                    f.write(f"  GPU {i}: {g.get('name', 'N/D')}\n")
                    f.write(f"    Temperatura: {g.get('temperature', 'N/D')}°C\n")
                    f.write(f"    Uso: {g.get('load', 'N/D')}%\n")
                    f.write(f"    Memória: {g.get('memory_used', 'N/D')} / {g.get('memory_total', 'N/D')}\n\n")
            else:
                f.write(f"  {gpu}\n\n")

        if battery:
            f.write("[BATERIA]\n")
            f.write(f"  Percentual: {battery.get('percent', 'N/D')}%\n")
            f.write(f"  Conectado : {battery.get('power_plugged', 'N/D')}\n")
            f.write(f"  Tempo restante: {battery.get('secsleft', 'N/D')} segundos\n\n")

        f.write("[DISCOS]\n")
        if not disks:
            f.write("  Nenhum disco encontrado ou acesso negado.\n\n")
        else:
            for d in disks:
                f.write(f"  Dispositivo: {d['device']}\n")
                f.write(f"    Montagem : {d['mountpoint']} ({d['fstype']})\n")
                f.write(f"    Total    : {bytes_to_human(d['total'])}\n")
                f.write(f"    Usado    : {bytes_to_human(d['used'])} ({d['percent']:.1f}%)\n")
                f.write(f"    Livre    : {bytes_to_human(d['free'])}\n\n")

        # SEÇÃO 2: REDE
        f.write("-" * 80 + "\n")
        f.write("SEÇÃO 2 - INFORMAÇÕES DE REDE\n")
        f.write("-" * 80 + "\n\n")

        for iface in nets:
            f.write(f"[Interface: {iface['name']}]\n")
            f.write(f"  Ativa (UP)      : {iface['isup']}\n")
            f.write(f"  Bytes enviados  : {bytes_to_human(iface['bytes_sent'])}\n")
            f.write(f"  Bytes recebidos : {bytes_to_human(iface['bytes_recv'])}\n")
            f.write("  Endereços:\n")
            for addr in iface["addresses"]:
                f.write(
                    f"    {addr['family']} - "
                    f"{addr['address']} / {addr['netmask']} "
                    f"(bcast: {addr['broadcast']})\n"
                )
            f.write("\n")

        # SEÇÃO 3: STRESS TESTS
        if include_stress_tests:
            f.write("-" * 80 + "\n")
            f.write("SEÇÃO 3 - TESTES DE STRESS\n")
            f.write("-" * 80 + "\n\n")

            f.write("[STRESS TEST - CPU]\n")
            if stress_cpu_results and "error" not in stress_cpu_results:
                for key, value in stress_cpu_results.items():
                    f.write(f"  {key}: {value}\n")
            else:
                f.write(f"  {stress_cpu_results.get('error', 'Não executado')}\n")
            f.write("\n")

            f.write("[STRESS TEST - RAM]\n")
            if stress_ram_results and "error" not in stress_ram_results:
                for key, value in stress_ram_results.items():
                    f.write(f"  {key}: {value}\n")
            else:
                f.write(f"  {stress_ram_results.get('error', 'Não executado')}\n")
            f.write("\n")

        # SEÇÃO 4: AUDITORIA DE SEGURANÇA
        if include_security_audit and security:
            f.write("-" * 80 + "\n")
            f.write("SEÇÃO 4 - AUDITORIA DE SEGURANÇA\n")
            f.write("-" * 80 + "\n\n")

            if "processes" in security:
                f.write("[AUDITORIA DE PROCESSOS]\n")
                procs = security["processes"]
                if isinstance(procs, dict) and "error" in procs:
                    f.write(f"  {procs['error']}\n")
                elif isinstance(procs, list):
                    for p in procs[:20]:  # Limita a 20 processos
                        f.write(f"  PID {p.get('pid')}: {p.get('name')} - CPU: {p.get('cpu_percent')}%\n")
                else:
                    f.write(f"  {procs}\n")
                f.write("\n")

            if "overclocking" in security:
                f.write("[DETECÇÃO DE FERRAMENTAS DE OVERCLOCK]\n")
                oc = security["overclocking"]
                if isinstance(oc, dict) and "error" in oc:
                    f.write(f"  {oc['error']}\n")
                elif isinstance(oc, list):
                    if oc:
                        for tool in oc:
                            f.write(f"  DETECTADO: {tool}\n")
                    else:
                        f.write("  Nenhuma ferramenta de overclock detectada.\n")
                else:
                    f.write(f"  {oc}\n")
                f.write("\n")

            if "network_anomalies" in security:
                f.write("[DETECÇÃO DE ANOMALIAS DE REDE]\n")
                anom = security["network_anomalies"]
                if isinstance(anom, dict) and "error" in anom:
                    f.write(f"  {anom['error']}\n")
                elif isinstance(anom, list):
                    if anom:
                        for a in anom:
                            f.write(f"  ANOMALIA: {a}\n")
                    else:
                        f.write("  Nenhuma anomalia detectada.\n")
                else:
                    f.write(f"  {anom}\n")
                f.write("\n")

        # SEÇÃO FINAL
        f.write("-" * 80 + "\n")
        f.write("OBSERVAÇÕES FINAIS\n")
        f.write("-" * 80 + "\n\n")
        f.write("Este relatório representa um snapshot completo do sistema no momento da geração.\n")
        f.write("Utilize em conjunto com outros artefatos e procedimentos periciais.\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("FIM DO RELATÓRIO\n")

    return filepath


# ============================================================================
# FUNÇÕES DE COMPATIBILIDADE (mantém as antigas para não quebrar código existente)
# ============================================================================

def generate_forensic_report(output_dir: str = "reports") -> str:
    """Versão simplificada (apenas info básica) - mantida para compatibilidade"""
    return generate_full_forensic_report(
        output_dir=output_dir,
        include_stress_tests=False,
        include_security_audit=False
    )


def generate_forensic_report_pdf(output_dir: str = "reports") -> str:
    """
    REMOVIDO: Geração de PDF foi desabilitada.
    Esta função agora gera apenas TXT para compatibilidade.
    """
    print("⚠️  Aviso: Geração de PDF foi desabilitada. Gerando apenas TXT.")
    return generate_full_forensic_report(
        output_dir=output_dir,
        include_stress_tests=False,
        include_security_audit=False
    )


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    print("Gerando relatório COMPLETO (TXT)...")
    print("Isso pode levar alguns segundos devido aos stress tests...\n")
    
    txt = generate_full_forensic_report(
        include_stress_tests=True,
        include_security_audit=True,
        stress_duration=3  # 3 segundos para teste rápido
    )
    print(f"✓ Relatório TXT completo gerado em: {txt}")
    
    print("\n" + "="*60)
    print("RELATÓRIO GERADO COM SUCESSO!")
    print("="*60)