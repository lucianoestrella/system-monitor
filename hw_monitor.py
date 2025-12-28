# file: hw_monitor.py
"""
Módulo responsável por coletar métricas de hardware em Windows e Linux.

Usa majoritariamente:
- psutil  -> CPU, RAM, discos, rede, bateria (básico)
- GPUtil  -> GPU
- smartctl -> Info de temperatura de discos (opcional, se instalado)
- pythonping -> ping para latência de rede (opcional)

Nem todas as máquinas/sistemas expõem todas as métricas. Em muitos casos,
a aplicação faz "best-effort" e retorna None onde não for possível obter o dado.
"""

import time
import subprocess
import platform
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

import psutil

try:
    import GPUtil
except ImportError:
    GPUtil = None  # Lidamos com ausência do GPUtil

try:
    # Opcional, principalmente para Windows
    import wmi  # type: ignore
except ImportError:
    wmi = None

try:
    from pythonping import ping
except ImportError:
    ping = None


# ---------- Data classes para estruturar as métricas ----------

@dataclass
class BatteryInfo:
    percent: Optional[float]
    secs_left: Optional[int]
    power_plugged: Optional[bool]
    voltage_mV: Optional[int] = None
    current_mA: Optional[int] = None
    cycle_count: Optional[int] = None
    health: Optional[str] = None


@dataclass
class GPUInfo:
    name: str
    load_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: Optional[float]


@dataclass
class CPUCoreInfo:
    core_index: int
    usage_percent: float
    frequency_mhz: Optional[float]
    temperature_c: Optional[float]


@dataclass
class CPUAndRAMInfo:
    cores: List[CPUCoreInfo]
    total_ram_gb: float
    used_ram_gb: float
    ram_usage_percent: float


@dataclass
class DiskInfo:
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    read_bytes_per_sec: float
    write_bytes_per_sec: float
    temperature_c: Optional[float]


@dataclass
class NetworkInfo:
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float
    latency_ms: Optional[float]


@dataclass
class SystemSnapshot:
    timestamp: float
    battery: Optional[BatteryInfo]
    gpus: List[GPUInfo]
    cpu_ram: CPUAndRAMInfo
    disks: List[DiskInfo]
    network: NetworkInfo


# ---------- Funções auxiliares de plataforma ----------

def _get_platform() -> str:
    return platform.system().lower()  # "windows", "linux", "darwin", etc.


# ---------- Battery ----------

def _get_battery_info() -> Optional[BatteryInfo]:
    """
    Tenta obter informações de bateria. psutil fornece apenas nível, tempo e AC.
    Para tensão/corrente/ciclos/saúde, é necessário ler interfaces do SO,
    que variam bastante entre fabricantes e sistemas.
    Aqui fazemos um best-effort em:
      - psutil
      - /sys/class/power_supply (Linux)
      - WMI Win32_Battery (Windows, se disponível)
    """
    battery = psutil.sensors_battery()
    percent = battery.percent if battery else None
    secs_left = battery.secsleft if battery else None
    power_plugged = battery.power_plugged if battery else None

    voltage_mV = None
    current_mA = None
    cycle_count = None
    health = None

    system = _get_platform()

    # Linux: tentar ler de /sys/class/power_supply/BAT*
    if system == "linux":
        try:
            import glob
            import os

            bat_paths = glob.glob("/sys/class/power_supply/BAT*")
            if bat_paths:
                bat_path = bat_paths[0]
                def read_int(file_name: str) -> Optional[int]:
                    full_path = os.path.join(bat_path, file_name)
                    if not os.path.exists(full_path):
                        return None
                    with open(full_path, "r") as f:
                        return int(f.read().strip())

                voltage_mV = read_int("voltage_now")
                if voltage_mV is not None:
                    voltage_mV = voltage_mV // 1000  # geralmente em µV

                current_mA = read_int("current_now")
                if current_mA is not None:
                    current_mA = current_mA // 1000  # geralmente em µA

                cycle_count = read_int("cycle_count")

                health_path = os.path.join(bat_path, "health")
                if os.path.exists(health_path):
                    with open(health_path, "r") as f:
                        health = f.read().strip()
        except Exception:
            pass

    # Windows: tentar via WMI (se biblioteca wmi estiver instalada)
    if system == "windows" and wmi is not None:
        try:
            c = wmi.WMI(namespace="root\\WMI")
            for bat in c.BatteryStatus():
                # Nem todos os campos são preenchidos em todos os sistemas
                # Muitos laptops não expõem tensão/corrente/ciclos via WMI.
                # Aqui apenas exemplificamos.
                # battery_voltage = getattr(bat, "Voltage", None)
                # battery_current = getattr(bat, "DischargeCurrent", None)
                # ...
                pass
        except Exception:
            pass

    if percent is None and voltage_mV is None:
        # Provavelmente não há bateria ou não detectável
        return None

    return BatteryInfo(
        percent=percent,
        secs_left=secs_left,
        power_plugged=power_plugged,
        voltage_mV=voltage_mV,
        current_mA=current_mA,
        cycle_count=cycle_count,
        health=health,
    )


# ---------- GPU ----------

def _get_gpu_info() -> List[GPUInfo]:
    """
    Coleta informações de GPU usando GPUtil, se disponível.
    """
    gpus_info: List[GPUInfo] = []
    if GPUtil is None:
        return gpus_info

    try:
        gpus = GPUtil.getGPUs()
        for g in gpus:
            gpus_info.append(
                GPUInfo(
                    name=g.name,
                    load_percent=g.load * 100.0,
                    memory_used_mb=g.memoryUsed,
                    memory_total_mb=g.memoryTotal,
                    temperature_c=g.temperature if hasattr(g, "temperature") else None,
                )
            )
    except Exception:
        # Em caso de erro, retornamos lista vazia
        pass

    return gpus_info


# ---------- CPU & RAM ----------

def _get_cpu_ram_info() -> CPUAndRAMInfo:
    """
    Coleta uso de CPU por núcleo, frequências e temperatura (se disponível),
    bem como consumo total de RAM.
    """
    # Uso de CPU por núcleo (interval=0.0 para não bloquear, mas
    # o calling code pode ter intervalo de refresh)
    per_core_usage = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freqs = psutil.cpu_freq(percpu=True)
    temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}

    # Mapear temperaturas por índice de core se possível
    core_temps: Dict[int, Optional[float]] = {}
    if temps:
        # psutil varia por plataforma, vamos tentar pegar algo como "coretemp" ou "cpu-thermal"
        for name, entries in temps.items():
            for idx, entry in enumerate(entries):
                # idx não necessariamente é o core físico, mas serve como aproximação
                core_temps[idx] = entry.current

    cores_info: List[CPUCoreInfo] = []
    for idx, usage in enumerate(per_core_usage):
        freq_mhz = None
        if cpu_freqs:
            if isinstance(cpu_freqs, list) and idx < len(cpu_freqs):
                freq_mhz = cpu_freqs[idx].current
            elif hasattr(cpu_freqs, "current"):
                freq_mhz = cpu_freqs.current

        temperature_c = core_temps.get(idx)

        cores_info.append(
            CPUCoreInfo(
                core_index=idx,
                usage_percent=usage,
                frequency_mhz=freq_mhz,
                temperature_c=temperature_c,
            )
        )

    vm = psutil.virtual_memory()
    total_ram_gb = vm.total / (1024 ** 3)
    used_ram_gb = vm.used / (1024 ** 3)
    ram_usage_percent = vm.percent

    return CPUAndRAMInfo(
        cores=cores_info,
        total_ram_gb=total_ram_gb,
        used_ram_gb=used_ram_gb,
        ram_usage_percent=ram_usage_percent,
    )


# ---------- Disks ----------

class _DiskIOTracker:
    """
    Utilitário interno para calcular taxa de leitura/escrita em bytes/s
    a partir de contadores cumulativos de psutil.disk_io_counters().
    """

    def __init__(self):
        self._last_ts = None
        self._last_counters = None

    def get_disk_io_rates(self) -> Dict[str, Dict[str, float]]:
        """
        Retorna dict: {device: {"read_bps": float, "write_bps": float}}
        """
        now = time.time()
        counters = psutil.disk_io_counters(perdisk=True)

        if self._last_ts is None or self._last_counters is None:
            self._last_ts = now
            self._last_counters = counters
            # Primeiro call retorna 0
            return {dev: {"read_bps": 0.0, "write_bps": 0.0} for dev in counters.keys()}

        dt = now - self._last_ts
        result: Dict[str, Dict[str, float]] = {}
        for dev, current in counters.items():
            prev = self._last_counters.get(dev)
            if prev is None or dt <= 0:
                result[dev] = {"read_bps": 0.0, "write_bps": 0.0}
            else:
                read_bps = (current.read_bytes - prev.read_bytes) / dt
                write_bps = (current.write_bytes - prev.write_bytes) / dt
                result[dev] = {"read_bps": max(0.0, read_bps), "write_bps": max(0.0, write_bps)}

        self._last_ts = now
        self._last_counters = counters
        return result


_disk_io_tracker = _DiskIOTracker()


def _get_disk_temperature(device: str) -> Optional[float]:
    """
    Tenta obter temperatura do disco usando smartctl, se disponível.
    Requer smartmontools instalado e permissões apropriadas.

    device em Linux tende a ser algo como '/dev/sda'.
    Em Windows, pode ser necessário mapear device para formatação aceita pelo smartctl.
    """
    try:
        # Comando típico: smartctl -A /dev/sda
        # Saída contém a temperatura (ex: ID# 194  Temperature_Celsius)
        output = subprocess.check_output(["smartctl", "-A", device], stderr=subprocess.STDOUT, text=True)
        for line in output.splitlines():
            if "Temperature_Celsius" in line or "Temperature" in line:
                parts = line.split()
                # Em geral o valor atual fica em alguma coluna numérica, aqui
                # fazemos uma heurística: o último valor inteiro da linha.
                for token in reversed(parts):
                    if token.isdigit():
                        return float(token)
    except Exception:
        pass
    return None


def _get_disks_info() -> List[DiskInfo]:
    """
    Coleta métricas de armazenamento: espaço e I/O, e tenta obter temperatura via smartctl.
    """
    disk_partitions = psutil.disk_partitions(all=False)
    io_rates = _disk_io_tracker.get_disk_io_rates()
    disks_info: List[DiskInfo] = []

    for p in disk_partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
        except PermissionError:
            continue

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        usage_percent = usage.percent

        # Mapear device para algo tipo /dev/sda em Linux; em Windows, p.device já vem
        device = p.device

        io_rate = io_rates.get(device, {"read_bps": 0.0, "write_bps": 0.0})
        read_bps = io_rate["read_bps"]
        write_bps = io_rate["write_bps"]

        # Tentar temperatura opcionalmente
        temp_c = None
        # Se smartctl estiver presente, você pode tentar /dev/sdX diretamente.
        # Em muitos casos, p.device já é algo utilizável; em casos mais complexos,
        # precisaria de mapeamento adicional.
        temp_c = _get_disk_temperature(device)

        disks_info.append(
            DiskInfo(
                device=device,
                mountpoint=p.mountpoint,
                fstype=p.fstype,
                total_gb=total_gb,
                used_gb=used_gb,
                free_gb=free_gb,
                usage_percent=usage_percent,
                read_bytes_per_sec=read_bps,
                write_bytes_per_sec=write_bps,
                temperature_c=temp_c,
            )
        )

    return disks_info


# ---------- Network ----------

class _NetIOTracker:
    """
    Utilitário interno para calcular taxa de upload/download em bytes/s
    a partir de contadores de psutil.net_io_counters().
    """

    def __init__(self):
        self._last_ts = None
        self._last_counters = None

    def get_net_rates(self) -> Dict[str, float]:
        """
        Retorna dict com 'bytes_sent_per_sec' e 'bytes_recv_per_sec'.
        """
        now = time.time()
        counters = psutil.net_io_counters()

        if self._last_ts is None or self._last_counters is None:
            self._last_ts = now
            self._last_counters = counters
            return {"bytes_sent_per_sec": 0.0, "bytes_recv_per_sec": 0.0}

        dt = now - self._last_ts
        if dt <= 0:
            return {"bytes_sent_per_sec": 0.0, "bytes_recv_per_sec": 0.0}

        sent_bps = (counters.bytes_sent - self._last_counters.bytes_sent) / dt
        recv_bps = (counters.bytes_recv - self._last_counters.bytes_recv) / dt

        self._last_ts = now
        self._last_counters = counters

        return {
            "bytes_sent_per_sec": max(0.0, sent_bps),
            "bytes_recv_per_sec": max(0.0, recv_bps),
        }


_net_io_tracker = _NetIOTracker()


def _get_latency_ms(host: str = "8.8.8.8", count: int = 1, timeout: int = 1000) -> Optional[float]:
    """
    Mede latência (ping) em ms usando pythonping, se disponível,
    senão tenta usar comando ping do sistema.
    """
    # Usando pythonping (recomendado, multiplataforma)
    if ping is not None:
        try:
            resp = ping(host, count=count, timeout=timeout / 1000.0)
            return resp.rtt_avg_ms
        except Exception:
            return None

    # Fallback para comando 'ping'
    system = _get_platform()
    try:
        if system == "windows":
            cmd = ["ping", host, "-n", str(count), "-w", str(timeout)]
        else:
            cmd = ["ping", host, "-c", str(count), "-W", str(int(timeout / 1000))]

        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        # Parsear média de tempo na saída (simplificado, não robusto para todos os idiomas)
        for line in out.splitlines():
            if "avg" in line or "mdev" in line:
                # exemplo linux: rtt min/avg/max/mdev = 12.345/23.456/...
                # exemplo windows: Média = XXms
                import re
                nums = re.findall(r"(\d+\.\d+|\d+)", line)
                if nums:
                    return float(nums[0])
    except Exception:
        return None

    return None


def _get_network_info() -> NetworkInfo:
    rates = _net_io_tracker.get_net_rates()
    latency_ms = _get_latency_ms()
    return NetworkInfo(
        bytes_sent_per_sec=rates["bytes_sent_per_sec"],
        bytes_recv_per_sec=rates["bytes_recv_per_sec"],
        latency_ms=latency_ms,
    )


# ---------- Interface principal para capturar um snapshot ----------

def get_system_snapshot() -> SystemSnapshot:
    """
    Captura um snapshot de todas as métricas de hardware em um único objeto.
    """
    timestamp = time.time()
    battery = _get_battery_info()
    gpus = _get_gpu_info()
    cpu_ram = _get_cpu_ram_info()
    disks = _get_disks_info()
    network = _get_network_info()

    return SystemSnapshot(
        timestamp=timestamp,
        battery=battery,
        gpus=gpus,
        cpu_ram=cpu_ram,
        disks=disks,
        network=network,
    )


def snapshot_to_dict(snapshot: SystemSnapshot) -> Dict[str, Any]:
    """
    Converte o snapshot em dict serializável (útil para logging/json).
    """
    # As data classes internas podem ser convertidas via asdict de forma recursiva
    return asdict(snapshot)