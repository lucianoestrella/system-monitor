# file: config.py
"""
Configurações globais da aplicação de monitoramento.
"""

REFRESH_INTERVAL_SECONDS = 1.0  # Intervalo padrão de atualização do dashboard

# Thresholds (exemplos) para destacar possíveis problemas
CPU_HIGH_USAGE_THRESHOLD = 85.0   # %
RAM_HIGH_USAGE_THRESHOLD = 90.0   # %
GPU_HIGH_USAGE_THRESHOLD = 85.0   # %
DISK_HIGH_USAGE_THRESHOLD = 90.0  # % espaço ocupado

# Lista de nomes/parciais de executáveis comumente associados a overclock/undervolt
KNOWN_OC_TOOL_NAMES = [
    "msiafterburner",
    "rivastatistics",
    "rtss",
    "intelxtu",
    "throttlestop",
    "precisionx",
    "evga precision",
    "radeonsoftware",
    "amd adrenaline",
]

# Threshold simples para “alto uso de rede” em bytes/s (exemplo)
HIGH_NETWORK_USAGE_BYTES_PER_SEC = 2 * 1024 * 1024  # ~2 MB/s