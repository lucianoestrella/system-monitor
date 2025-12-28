# file: security.py
"""
Módulo de Segurança e Auditoria.

Funcionalidades:
- Escanear processos ativos
- Detectar ferramentas de overclock/undervolt conhecidas por nome
- Identificar processos com uso de rede "alto/anômalo" (heurística simples)
- Detectar picos anormais de tráfego de rede (download/upload)
- Detectar tentativas de brute-force SSH em logs do Linux
- Heurística de brute-force baseada em conexões (Windows + Linux)

Limitações:
- Per-process network usage via psutil não é trivial em todas as plataformas;
  aqui utilizamos uma heurística baseada em contagem de conexões e snapshots
  múltiplos (diferença de bytes globais ainda assim é por sistema, não por processo).
- Para auditorias mais avançadas, seria necessário integrar com ferramentas
  de firewall/sistema, ou ler /proc/<pid>/net em Linux, etc.
"""

import time
import os
import platform
import math
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Deque, Tuple
from collections import deque, Counter

import psutil

from config import KNOWN_OC_TOOL_NAMES, HIGH_NETWORK_USAGE_BYTES_PER_SEC
from hw_monitor import _NetIOTracker, get_system_snapshot


# ========== Estruturas de dados ==========

@dataclass
class SuspiciousProcess:
    pid: int
    name: str
    reason: str
    extra_info: Optional[str] = None


@dataclass
class NetSpikeEvent:
    direction: str          # "download" ou "upload"
    current_kb_s: float
    avg_kb_s: float
    threshold_kb_s: float


# ========== Detecção de ferramentas de overclock ==========

def _is_known_oc_tool(proc_name: str) -> bool:
    """
    Checa se o nome do processo bate com alguma substring de ferramentas
    conhecidas de overclock.
    """
    lower = proc_name.lower()
    for pattern in KNOWN_OC_TOOL_NAMES:
        if pattern in lower:
            return True
    return False


def scan_overclock_tools() -> List[SuspiciousProcess]:
    """
    Retorna lista de processos que aparentemente são ferramentas de overclock/undervolt.
    """
    suspects: List[SuspiciousProcess] = []

    for p in psutil.process_iter(attrs=["pid", "name"]):
        name = p.info.get("name") or ""
        if not name:
            continue
        try:
            if _is_known_oc_tool(name):
                suspects.append(
                    SuspiciousProcess(
                        pid=p.info["pid"],
                        name=name,
                        reason="Possível ferramenta de overclock/undervolt",
                    )
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return suspects


# ========== Detecção de anomalias de rede por processo ==========

def scan_network_anomalies(sample_duration: float = 3.0) -> List[SuspiciousProcess]:
    """
    Heurística simples de "uso de rede anômalo".
    Aqui, como não é trivial obter bytes/s por processo com psutil puro
    em todas as plataformas, fazemos:

    1. Medimos taxa global de rede ao longo de 'sample_duration'.
    2. Identificamos processos com muitas conexões ativas ou portas incomuns.
    3. Se a taxa global for muito alta, listamos processos com conexões externas
       como suspeitos.

    Observação: isso é apenas um "triage", não uma auditoria formal.
    """
    net_tracker = _NetIOTracker()

    # Primeira leitura
    _ = net_tracker.get_net_rates()
    time.sleep(sample_duration)
    rates = net_tracker.get_net_rates()

    total_recv_bps = rates["bytes_recv_per_sec"]
    total_sent_bps = rates["bytes_sent_per_sec"]

    high_traffic = (
        total_recv_bps > HIGH_NETWORK_USAGE_BYTES_PER_SEC
        or total_sent_bps > HIGH_NETWORK_USAGE_BYTES_PER_SEC
    )

    suspects: List[SuspiciousProcess] = []

    # Mapeia processos com muitas conexões externas (estado ESTABLISHED)
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        conns = []

    proc_conn_count: Dict[int, int] = {}

    for c in conns:
        pid = c.pid
        if pid is None:
            continue
        proc_conn_count[pid] = proc_conn_count.get(pid, 0) + 1

    for pid, count in proc_conn_count.items():
        try:
            p = psutil.Process(pid)
            name = p.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        # Heurística:
        # - Se tráfego global está alto
        # - E o processo tem muitas conexões
        # => marcamos como suspeito
        if high_traffic and count >= 5:
            suspects.append(
                SuspiciousProcess(
                    pid=pid,
                    name=name,
                    reason="Muitas conexões de rede enquanto tráfego global está alto",
                    extra_info=f"{count} conexões inet",
                )
            )

    return suspects


# ========== Detector de picos de tráfego de rede ==========

class NetworkSpikeDetector:
    """
    Detector simples de picos de tráfego de rede baseado em média móvel.
    Guarda últimas N amostras de download/upload.
    """
    def __init__(self, window_size: int = 60, spike_factor: float = 3.0):
        self.window_size = window_size
        self.spike_factor = spike_factor
        self.down_history: Deque[float] = deque(maxlen=window_size)
        self.up_history: Deque[float] = deque(maxlen=window_size)

    def add_sample(self, down_bytes_per_sec: float, up_bytes_per_sec: float) -> List[NetSpikeEvent]:
        """Adiciona uma amostra e retorna lista de eventos de pico detectados agora."""
        down_kb = down_bytes_per_sec / 1024.0
        up_kb = up_bytes_per_sec / 1024.0

        self.down_history.append(down_kb)
        self.up_history.append(up_kb)

        events: List[NetSpikeEvent] = []

        # Só começa a detectar depois que temos histórico suficiente
        if len(self.down_history) < max(10, self.window_size // 4):
            return events

        def stats(values: Deque[float]) -> Tuple[float, float]:
            n = len(values)
            avg = sum(values) / n
            var = sum((v - avg) ** 2 for v in values) / n
            std = math.sqrt(var)
            return avg, std

        # Download
        avg_down, std_down = stats(self.down_history)
        thr_down = avg_down * self.spike_factor if avg_down > 0 else 0

        if down_kb > max(thr_down, avg_down + 3 * std_down) and down_kb > 50:  # >50 KB/s para evitar ruído
            events.append(NetSpikeEvent(
                direction="download",
                current_kb_s=down_kb,
                avg_kb_s=avg_down,
                threshold_kb_s=max(thr_down, avg_down + 3 * std_down),
            ))

        # Upload
        avg_up, std_up = stats(self.up_history)
        thr_up = avg_up * self.spike_factor if avg_up > 0 else 0

        if up_kb > max(thr_up, avg_up + 3 * std_up) and up_kb > 50:
            events.append(NetSpikeEvent(
                direction="upload",
                current_kb_s=up_kb,
                avg_kb_s=avg_up,
                threshold_kb_s=max(thr_up, avg_up + 3 * std_up),
            ))

        return events


# Instância global do detector
net_spike_detector = NetworkSpikeDetector(window_size=60, spike_factor=3.0)


def check_network_spikes() -> List[NetSpikeEvent]:
    """Usa o snapshot atual para verificar se há picos de rede anormais."""
    snap = get_system_snapshot()
    events = net_spike_detector.add_sample(
        down_bytes_per_sec=snap.network.bytes_recv_per_sec,
        up_bytes_per_sec=snap.network.bytes_sent_per_sec,
    )
    return events


# ========== Detecção de brute-force SSH (Linux) ==========

def detect_ssh_bruteforce_linux(
    logfile_paths=("/var/log/auth.log", "/var/log/secure"),
    min_failures: int = 5,
) -> Dict[str, int]:
    """
    Analisa rapidamente logs de autenticação em Linux para detectar possíveis ataques de força bruta em SSH.
    Retorna um dict {ip: contagem_de_falhas} para IPs suspeitos.
    """
    if platform.system() != "Linux":
        return {}

    log_path = None
    for p in logfile_paths:
        if os.path.exists(p):
            log_path = p
            break

    if not log_path:
        return {}

    # Lê só o final do arquivo para não pesar
    try:
        with open(log_path, "rb") as f:
            try:
                f.seek(-200_000, os.SEEK_END)  # últimos ~200KB
            except OSError:
                f.seek(0)
            data = f.read().decode(errors="ignore")
    except Exception:
        return {}

    # Contar padrões de falha por IP
    # Exemplo de linhas:
    # "Failed password for invalid user test from 1.2.3.4 port 54321 ssh2"
    # "Failed password for root from 5.6.7.8 port 45678 ssh2"
    pattern = re.compile(r"Failed password .* from (\d+\.\d+\.\d+\.\d+) ")

    counter = Counter(pattern.findall(data))

    suspicious = {ip: cnt for ip, cnt in counter.items() if cnt >= min_failures}
    return suspicious


# ========== Scan completo de segurança ==========

def full_security_scan() -> Dict[str, List[SuspiciousProcess]]:
    """
    Executa um "scan completo": overclock tools + anomalias de rede.
    """
    overclock = scan_overclock_tools()
    net_anomalies = scan_network_anomalies()
    return {
        "overclock_tools": overclock,
        "network_anomalies": net_anomalies,
    }