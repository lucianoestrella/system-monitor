# file: network_monitor.py
"""
Ferramentas de monitoramento de rede e descoberta de hosts.

Funcionalidades:
- Descobrir IP local e faixa de rede (ex.: 192.168.0.0/24)
- Scan de hosts ativos (ping sweep simples)
- Scan de portas básicas em um host (port scan leve)
- Listar conexões de rede da máquina local (tipo netstat)
- Detectar sessões de acesso remoto (SSH/RDP/VNC) em tempo real
- Heurística para brute-force baseado em número de conexões remotas
"""

import ipaddress
import socket
import concurrent.futures
from typing import List, Dict, Tuple, Optional

import psutil
from pythonping import ping
from dataclasses import dataclass
from collections import Counter


# ---------- Utilidades básicas de IP / rede ----------

def get_local_ip() -> Optional[str]:
    """
    Retorna o IP local (IPv4) preferencial.
    """
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip.startswith("127."):
            # Tenta outro método
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
        return local_ip
    except Exception:
        return None


def guess_local_network_cidr() -> Optional[str]:
    """
    Tenta adivinhar a faixa de rede local (ex.: 192.168.0.0/24)
    com base no IP local.
    """
    ip = get_local_ip()
    if not ip:
        return None

    # Heurística simples: assume /24
    # Ex.: 192.168.0.23 -> 192.168.0.0/24
    parts = ip.split(".")
    if len(parts) != 4:
        return None

    network = ".".join(parts[:3]) + ".0/24"
    return network


# ---------- Scan de hosts ----------

def is_host_up(ip: str, timeout: float = 0.5) -> bool:
    """
    Retorna True se o host responder a ping.
    """
    try:
        resp = ping(ip, count=1, timeout=timeout, verbose=False)
        return resp.success()
    except Exception:
        return False


def scan_network_hosts(cidr: str, max_workers: int = 100) -> List[str]:
    """
    Faz um ping sweep em uma rede (ex.: 192.168.0.0/24)
    e retorna uma lista de IPs que responderam.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    ips = [str(ip) for ip in network.hosts()]

    alive_ips: List[str] = []

    def check_ip(ip_addr: str):
        if is_host_up(ip_addr):
            alive_ips.append(ip_addr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(check_ip, ips))

    return sorted(alive_ips)


# ---------- Port scan básico ----------

COMMON_PORTS = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    445: "SMB",
    139: "NetBIOS",
    3389: "RDP",
}


def is_port_open(ip: str, port: int, timeout: float = 0.5) -> bool:
    """
    Tenta conexão TCP em uma porta.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()


def scan_host_ports(ip: str, ports: List[int] = None, max_workers: int = 100) -> List[Tuple[int, str]]:
    """
    Escaneia um conjunto de portas em um host.
    Retorna uma lista de (porta, descrição) abertas.
    """
    if ports is None:
        ports = list(COMMON_PORTS.keys())

    open_ports: List[Tuple[int, str]] = []

    def check_port(p: int):
        if is_port_open(ip, p):
            desc = COMMON_PORTS.get(p, "")
            open_ports.append((p, desc))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(check_port, ports))

    return sorted(open_ports, key=lambda x: x[0])


# ---------- Conexões locais (tipo netstat) ----------

def list_local_connections(limit: int = 50) -> List[Dict]:
    """
    Lista conexões de rede da máquina local (TCP/UDP) usando psutil.net_connections().
    """
    conns_info: List[Dict] = []

    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return conns_info

    for c in conns[:limit]:
        laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
        raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-"
        conns_info.append(
            {
                "type": c.type,  # socket.SOCK_STREAM / SOCK_DGRAM
                "status": c.status,
                "laddr": laddr,
                "raddr": raddr,
                "pid": c.pid,
            }
        )

    return conns_info


# ---------- Monitoramento de acessos remotos (SSH/RDP/VNC) ----------

REMOTE_ACCESS_PORTS = {
    22: "SSH",
    3389: "RDP",
    5900: "VNC",
    5901: "VNC",
    5902: "VNC",
    5903: "VNC",
    5904: "VNC",
    5905: "VNC",
}


@dataclass
class RemoteAccessSession:
    proto: str      # "TCP" / "UDP"
    service: str    # "SSH"/"RDP"/"VNC"/"Desconhecido"
    local_addr: str
    remote_addr: str
    status: str
    pid: Optional[int]
    process_name: Optional[str]


def list_remote_access_sessions() -> List[RemoteAccessSession]:
    """
    Lista conexões que parecem ser acessos remotos (SSH, RDP, VNC) em tempo real.
    Funciona em Windows e Linux (depende dos dados expostos pelo SO/psutil).
    """
    sessions: List[RemoteAccessSession] = []

    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return sessions

    for c in conns:
        # Só conexões TCP de interesse
        if c.type != socket.SOCK_STREAM:
            continue
        if not c.laddr or not c.raddr:
            continue

        laddr_ip, laddr_port = c.laddr.ip, c.laddr.port
        raddr_ip, raddr_port = c.raddr.ip, c.raddr.port if c.raddr else (None, None)

        # Porta local ou remota de acesso remoto?
        service = None
        if laddr_port in REMOTE_ACCESS_PORTS:
            service = REMOTE_ACCESS_PORTS[laddr_port]
        elif raddr_port in REMOTE_ACCESS_PORTS:
            service = REMOTE_ACCESS_PORTS[raddr_port]

        if not service:
            continue

        try:
            proc = psutil.Process(c.pid) if c.pid else None
            pname = proc.name() if proc else None
        except Exception:
            pname = None

        sess = RemoteAccessSession(
            proto="TCP",
            service=service,
            local_addr=f"{laddr_ip}:{laddr_port}",
            remote_addr=f"{raddr_ip}:{raddr_port}",
            status=c.status,
            pid=c.pid,
            process_name=pname,
        )
        sessions.append(sess)

    return sessions


# ---------- Heurística de brute-force por conexões ----------

def detect_remote_login_bruteforce_from_conns(min_conns: int = 10) -> Dict[str, int]:
    """
    Heurística simples: conta quantas conexões recentes para portas de acesso remoto
    vieram de cada IP remoto. Se passar de min_conns, marca como suspeito.
    Funciona em Windows e Linux, mas é apenas uma aproximação (não lê logs reais).
    Retorna {ip: contagem_de_conexoes}.
    """
    suspicious: Dict[str, int] = {}

    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return suspicious

    counter = Counter()

    for c in conns:
        if c.type != socket.SOCK_STREAM:
            continue
        if not c.laddr or not c.raddr:
            continue

        lport = c.laddr.port
        rport = c.raddr.port
        rip = c.raddr.ip

        # Porta de acesso remoto?
        if lport in REMOTE_ACCESS_PORTS or rport in REMOTE_ACCESS_PORTS:
            counter[rip] += 1

    for ip, cnt in counter.items():
        if cnt >= min_conns:
            suspicious[ip] = cnt

    return suspicious