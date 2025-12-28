# file: stress.py
"""
Módulo de stress de sistema.

ATENÇÃO:
- Use apenas em ambiente de testes.
- Pode travar a máquina temporariamente, aquecer CPU/GPU e causar perda de dados
  se você tiver arquivos não salvos.
- NÃO use em servidores de produção.

Funções:
- start_cpu_stress(num_threads, intensity, duration)
- start_ram_stress(target_mb, duration)
- start_full_stress(duration)  # stress pesado combinado (CPU + RAM)
"""

import threading
import time
import os
from typing import List

import psutil


# =========================
#   STRESS DE CPU
# =========================

def _cpu_worker(stop_event, intensity: float):
    """
    Worker de CPU.
    intensity entre 0 e 1.
      1.0 -> 100% busy (sem pausas)
      0.5 -> ~50% (busy + sleep)
    """
    if intensity <= 0:
        intensity = 0.1
    if intensity > 1.0:
        intensity = 1.0

    busy_time = intensity * 0.1
    sleep_time = (1.0 - intensity) * 0.1

    while not stop_event.is_set():
        start = time.time()
        # Loop "ocupado" (busy-wait)
        while (time.time() - start) < busy_time and not stop_event.is_set():
            pass
        # Pequena pausa para controlar intensidade
        if sleep_time > 0 and not stop_event.is_set():
            time.sleep(sleep_time)


def start_cpu_stress(num_threads: int = None, intensity: float = 1.0, duration: float = 30.0):
    """
    Inicia stress de CPU.

    :param num_threads: número de threads de CPU (default = todos os núcleos lógicos)
    :param intensity: 0.1 a 1.0 (1.0 = 100% uso possível)
    :param duration: duração em segundos
    """
    if num_threads is None or num_threads <= 0:
        num_threads = os.cpu_count() or 4

    if duration <= 0:
        duration = 10.0

    stop_event = threading.Event()
    threads: List[threading.Thread] = []

    for _ in range(num_threads):
        t = threading.Thread(target=_cpu_worker, args=(stop_event, intensity), daemon=True)
        threads.append(t)
        t.start()

    try:
        time.sleep(duration)
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=1.0)


# =========================
#   STRESS DE RAM
# =========================

def start_ram_stress(target_mb: int = 512, duration: float = 30.0):
    """
    Aloca um grande bloco de RAM e mantém durante 'duration' segundos.

    - target_mb é limitado a uma fração da RAM total para evitar crash imediato.
    """
    vm = psutil.virtual_memory()
    total_mb = vm.total / (1024 * 1024)

    # Limitar a, no máximo, ~70% da RAM total
    max_safe_mb = int(total_mb * 0.7)
    if target_mb > max_safe_mb:
        target_mb = max_safe_mb

    if target_mb <= 0:
        target_mb = 128

    if duration <= 0:
        duration = 10.0

    # Tentar alocar
    try:
        print(f"[RAM STRESS] Alocando ~{target_mb} MB (máx seguro ~70% da RAM).")
        block = bytearray(target_mb * 1024 * 1024)
        # Tocar em algumas posições para realmente alocar nas páginas físicas
        step = max(1, len(block) // 50)
        for i in range(0, len(block), step):
            block[i] = (block[i] + 1) % 256

        time.sleep(duration)
    except MemoryError:
        print("[RAM STRESS] Falha ao alocar RAM (MemoryError).")
    finally:
        # Deixar o GC liberar
        del block


# =========================
#   STRESS COMBINADO
# =========================

def start_full_stress(duration: float = 60.0, cpu_intensity: float = 1.0):
    """
    Stress pesado de sistema (CPU + RAM), com LIMITES DE SEGURANÇA.

    - Usa todos os núcleos lógicos da CPU.
    - Aloca até ~70% da RAM total.
    - Dura 'duration' segundos (limitado para evitar rodar para sempre).

    ATENÇÃO: isso pode deixar o sistema BEM lento durante o período.
    """

    # Limites de segurança adicionais
    if duration <= 0:
        duration = 10.0
    if duration > 600:  # máx 10 minutos
        duration = 600.0

    # Determinar RAM alvo (por ex. 60% da RAM total)
    vm = psutil.virtual_memory()
    total_mb = vm.total / (1024 * 1024)
    target_mb = int(total_mb * 0.6)

    print(f"[FULL STRESS] Iniciando stress combinado por ~{duration:.0f}s")
    print(f"  - CPU: {os.cpu_count() or 4} threads, intensidade={cpu_intensity}")
    print(f"  - RAM: ~{target_mb} MB (≈60% da RAM total)")

    # Eventos e threads
    stop_event = threading.Event()
    cpu_threads: List[threading.Thread] = []

    def cpu_stress_runner():
        _cpu_worker(stop_event, cpu_intensity)

    # Inicia CPU threads
    num_threads = os.cpu_count() or 4
    for _ in range(num_threads):
        t = threading.Thread(target=cpu_stress_runner, daemon=True)
        cpu_threads.append(t)
        t.start()

    # Inicia RAM stress em thread separada
    ram_thread = threading.Thread(
        target=start_ram_stress,
        kwargs={"target_mb": target_mb, "duration": duration},
        daemon=True,
    )
    ram_thread.start()

    # Aguarda duração
    try:
        time.sleep(duration)
    finally:
        # Para CPU
        stop_event.set()
        for t in cpu_threads:
            t.join(timeout=1.0)

        # Garante fim do RAM stress
        ram_thread.join(timeout=5.0)

        print("[FULL STRESS] Stress combinado finalizado.")