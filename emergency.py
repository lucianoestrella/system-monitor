"""
Módulo de Proteção de Emergência para Peritos Forenses

Funcionalidades:
1. Desligamento programado (timer)
2. Desligamento remoto (via HTTP)
3. Colapso drástico do sistema (CPU + RAM + Disco)
4. Limpeza de logs sensíveis
5. Bloqueio de usuário

ATENÇÃO: Este módulo deve ser usado apenas em situações legítimas de emergência
e com autorização apropriada para o sistema em questão.
"""

import os
import sys
import time
import threading
import subprocess
import socket
import tempfile
import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
import platform
import psutil
import shutil

# ============================================================================
# CONFIGURAÇÕES DE SEGURANÇA
# ============================================================================

# Senha de emergência (SHA256 hash)
# Para usar: defina uma senha e calcule seu hash SHA256
# Exemplo: echo -n "senha123" | sha256sum
EMERGENCY_PASSWORD_HASH = "964863940240a709fae9638760247f1b8f1b6f8fde0ade81024b07b9e012d64f"  # Defina o hash SHA256 da sua senha aqui

# Porta para controle remoto (HTTP)
REMOTE_CONTROL_PORT = 8080

# ============================================================================
# FUNÇÕES DE DESLIGAMENTO
# ============================================================================

def shutdown_system(delay_seconds: int = 0, force: bool = True) -> bool:
    """
    Desliga o sistema após um delay.
    
    Args:
        delay_seconds: Segundos para aguardar antes de desligar
        force: Forçar fechamento de aplicativos (Windows) ou usar shutdown now (Linux)
    
    Returns:
        True se o comando foi executado, False caso contrário
    """
    try:
        if delay_seconds > 0:
            print(f"[EMERGENCY] Sistema será desligado em {delay_seconds} segundos...")
            time.sleep(delay_seconds)
        
        system = platform.system()
        
        if system == "Windows":
            # Windows
            force_flag = "/f" if force else ""
            cmd = f"shutdown /s /t 0 {force_flag}"
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
            
        elif system == "Linux":
            # Linux
            force_flag = "now" if force else "+0"
            cmd = f"shutdown -h {force_flag}"
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
            
        elif system == "Darwin":  # macOS
            cmd = "sudo shutdown -h now"
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
            
        else:
            print(f"[EMERGENCY] Sistema operacional não suportado: {system}")
            return False
            
    except Exception as e:
        print(f"[EMERGENCY] Erro ao desligar sistema: {e}")
        return False


def schedule_shutdown(minutes: int = 5) -> threading.Thread:
    """
    Agenda desligamento após X minutos.
    
    Args:
        minutes: Minutos até o desligamento
    
    Returns:
        Thread do timer (pode ser cancelada com timer.cancel())
    """
    def shutdown_task():
        print(f"[EMERGENCY] Desligamento programado para {minutes} minutos...")
        time.sleep(minutes * 60)
        shutdown_system()
    
    timer = threading.Thread(target=shutdown_task, daemon=True)
    timer.start()
    return timer


def cancel_scheduled_shutdown() -> bool:
    """
    Cancela um desligamento programado.
    
    Returns:
        True se cancelado com sucesso
    """
    try:
        system = platform.system()
        
        if system == "Windows":
            cmd = "shutdown /a"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
            
        elif system == "Linux":
            cmd = "shutdown -c"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
            
        else:
            print(f"[EMERGENCY] Cancelamento não suportado em {system}")
            return False
            
    except Exception as e:
        print(f"[EMERGENCY] Erro ao cancelar desligamento: {e}")
        return False

# ============================================================================
# SERVIDOR DE CONTROLE REMOTO (HTTP SIMPLES)
# ============================================================================

class RemoteControlServer:
    """Servidor HTTP simples para controle remoto do sistema."""
    
    def __init__(self, port: int = REMOTE_CONTROL_PORT, password_hash: Optional[str] = None):
        self.port = port
        self.password_hash = password_hash
        self.server = None
        self.running = False
        
    def start(self) -> bool:
        """Inicia o servidor de controle remoto."""
        try:
            import http.server
            import urllib.parse
            
            class EmergencyHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    # Parse query parameters
                    parsed = urllib.parse.urlparse(self.path)
                    query = urllib.parse.parse_qs(parsed.query)
                    
                    # Verificar senha se configurada
                    if self.server.password_hash:
                        provided_hash = query.get('auth', [''])[0]
                        if provided_hash != self.server.password_hash:
                            self.send_response(403)
                            self.end_headers()
                            self.wfile.write(b'Access denied')
                            return
                    
                    # Processar comandos
                    command = query.get('cmd', [''])[0]
                    response = b'OK'
                    
                    if command == 'shutdown':
                        threading.Thread(target=shutdown_system, daemon=True).start()
                        response = b'Shutdown initiated'
                    elif command == 'status':
                        response = b'System monitor emergency module active'
                    elif command == 'cancel':
                        cancel_scheduled_shutdown()
                        response = b'Shutdown cancelled'
                    else:
                        response = b'Unknown command'
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(response)
                
                def log_message(self, format, *args):
                    # Silenciar logs
                    pass
            
            # Monkey patch para passar o servidor como atributo
            handler = EmergencyHandler
            handler.server = self
            
            self.server = http.server.HTTPServer(('0.0.0.0', self.port), handler)
            self.running = True
            
            print(f"[EMERGENCY] Servidor de controle remoto iniciado na porta {self.port}")
            print(f"[EMERGENCY] URL de exemplo: http://IP_DA_MAQUINA:{self.port}/?cmd=shutdown&auth=SENHA_HASH")
            
            # Executar em thread separada
            server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            server_thread.start()
            return True
            
        except Exception as e:
            print(f"[EMERGENCY] Erro ao iniciar servidor: {e}")
            return False
    
    def stop(self):
        """Para o servidor de controle remoto."""
        if self.server:
            self.server.shutdown()
            self.running = False
            print("[EMERGENCY] Servidor de controle remoto parado")

# ============================================================================
# COLAPSO DO SISTEMA (MODO DRÁSTICO)
# ============================================================================

class SystemCollapser:
    """Classe para colapsar recursos do sistema de forma drástica."""
    
    def __init__(self):
        self.cpu_threads = []
        self.ram_threads = []
        self.disk_threads = []
        self.running = False
        
    def start_full_collapse(self, duration_seconds: int = 300) -> None:
        """
        Inicia colapso completo do sistema (CPU + RAM + Disco).
        
        Args:
            duration_seconds: Duração do colapso em segundos (padrão: 5 minutos)
        """
        if self.running:
            print("[EMERGENCY] Colapso já em andamento")
            return
        
        self.running = True
        print(f"[EMERGENCY] Iniciando colapso do sistema por {duration_seconds} segundos")
        print("[EMERGENCY] ATENÇÃO: Sistema ficará extremamente lento/não responsivo!")
        
        # Iniciar threads de colapso
        self._start_cpu_collapse(duration_seconds)
        self._start_ram_collapse(duration_seconds)
        self._start_disk_collapse(duration_seconds)
        
        # Timer para parar automaticamente
        def stop_timer():
            time.sleep(duration_seconds)
            self.stop_collapse()
        
        threading.Thread(target=stop_timer, daemon=True).start()
    
    def _start_cpu_collapse(self, duration: int):
        """Colapsa CPU usando todos os núcleos."""
        def cpu_killer():
            print(f"[EMERGENCY] Colapso de CPU iniciado")
            end_time = time.time() + duration
            
            while time.time() < end_time and self.running:
                # Cálculo intensivo
                for _ in range(1000000):
                    _ = hashlib.sha256(str(random.random()).encode()).hexdigest()
            
            print("[EMERGENCY] Colapso de CPU finalizado")
        
        # Usar todos os núcleos disponíveis
        num_cores = psutil.cpu_count(logical=True)
        for i in range(num_cores):
            thread = threading.Thread(target=cpu_killer, daemon=True)
            thread.start()
            self.cpu_threads.append(thread)
    
    def _start_ram_collapse(self, duration: int):
        """Colapsa RAM alocando memória máxima possível."""
        def ram_killer():
            print(f"[EMERGENCY] Colapso de RAM iniciado")
            end_time = time.time() + duration
            
            # Tentar alocar ~80% da RAM disponível
            try:
                total_memory = psutil.virtual_memory().total
                target_memory = int(total_memory * 0.8)
                chunk_size = 100 * 1024 * 1024  # 100 MB por chunk
                
                memory_chunks = []
                allocated = 0
                
                while time.time() < end_time and self.running and allocated < target_memory:
                    try:
                        # Alocar chunk de memória
                        chunk = bytearray(chunk_size)
                        memory_chunks.append(chunk)
                        allocated += chunk_size
                        
                        # Preencher com dados aleatórios
                        for j in range(0, len(chunk), 4096):
                            chunk[j:j+4096] = os.urandom(4096)
                            
                    except MemoryError:
                        print(f"[EMERGENCY] Memória esgotada após alocar {allocated/(1024*1024):.1f} MB")
                        break
                
                # Manter memória alocada até o fim
                while time.time() < end_time and self.running:
                    time.sleep(0.1)
                
                # Liberar memória
                memory_chunks.clear()
                
            except Exception as e:
                print(f"[EMERGENCY] Erro no colapso de RAM: {e}")
            
            print("[EMERGENCY] Colapso de RAM finalizado")
        
        thread = threading.Thread(target=ram_killer, daemon=True)
        thread.start()
        self.ram_threads.append(thread)
    
    def _start_disk_collapse(self, duration: int):
        """Colapsa disco com escrita intensiva."""
        def disk_killer():
            print(f"[EMERGENCY] Colapso de disco iniciado")
            end_time = time.time() + duration
            
            try:
                # Criar arquivo temporário grande
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"emergency_collapse_{int(time.time())}.dat")
                
                with open(temp_file, 'wb') as f:
                    chunk_size = 10 * 1024 * 1024  # 10 MB
                    written = 0
                    target_size = 5 * 1024 * 1024 * 1024  # 5 GB máximo
                    
                    while time.time() < end_time and self.running and written < target_size:
                        # Escrever dados aleatórios
                        data = os.urandom(chunk_size)
                        f.write(data)
                        f.flush()
                        written += chunk_size
                        
                        # Ler aleatoriamente para aumentar I/O
                        if random.random() < 0.3:
                            f.seek(random.randint(0, written - 1))
                            f.read(random.randint(1024, 1024*1024))
                
                # Remover arquivo
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                print(f"[EMERGENCY] Erro no colapso de disco: {e}")
            
            print("[EMERGENCY] Colapso de disco finalizado")
        
        thread = threading.Thread(target=disk_killer, daemon=True)
        thread.start()
        self.disk_threads.append(thread)
    
    def stop_collapse(self):
        """Para todos os processos de colapso."""
        self.running = False
        
        # Aguardar threads terminarem
        for thread in self.cpu_threads + self.ram_threads + self.disk_threads:
            try:
                thread.join(timeout=2.0)
            except:
                pass
        
        self.cpu_threads.clear()
        self.ram_threads.clear()
        self.disk_threads.clear()
        
        print("[EMERGENCY] Colapso do sistema interrompido")

# ============================================================================
# LIMPEZA DE LOGS SENSÍVEIS
# ============================================================================

def clean_sensitive_logs(patterns: List[str] = None) -> int:
    """
    Remove arquivos de log que podem conter informações sensíveis.
    
    Args:
        patterns: Lista de padrões de arquivos para limpar
    
    Returns:
        Número de arquivos removidos
    """
    if patterns is None:
        patterns = [
            # Windows
            "C:\\Windows\\System32\\winevt\\Logs\\*.evtx",
            "C:\\Users\\*\\AppData\\Local\\Temp\\*",
            "C:\\Windows\\Temp\\*",
            
            # Linux
            "/var/log/*.log",
            "/var/log/auth.log*",
            "/var/log/syslog*",
            "/tmp/*",
            "/var/tmp/*",
            
            # macOS
            "/private/var/log/*.log",
            "/Library/Logs/*.log",
            "~/Library/Logs/*.log"
        ]
    
    removed_count = 0
    
    for pattern in patterns:
        try:
            # Expandir pattern
            if platform.system() == "Windows":
                import glob
                files = glob.glob(pattern, recursive=True)
            else:
                import fnmatch
                import os
                files = []
                for root, dirnames, filenames in os.walk(os.path.expanduser(pattern.split('*')[0])):
                    for filename in fnmatch.filter(filenames, os.path.basename(pattern)):
                        files.append(os.path.join(root, filename))
            
            # Remover arquivos
            for file_path in files:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        removed_count += 1
                        print(f"[EMERGENCY] Removido: {file_path}")
                except Exception as e:
                    print(f"[EMERGENCY] Erro ao remover {file_path}: {e}")
                    
        except Exception as e:
            print(f"[EMERGENCY] Erro ao processar pattern {pattern}: {e}")
    
    return removed_count

# ============================================================================
# BLOQUEIO DE USUÁRIO
# ============================================================================

def lock_current_user() -> bool:
    """
    Bloqueia a sessão do usuário atual.
    
    Returns:
        True se bloqueado com sucesso
    """
    try:
        system = platform.system()
        
        if system == "Windows":
            # Bloquear workstation Windows
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return True
            
        elif system == "Linux":
            # Depende do gerenciador de sessão
            # Tentar comandos comuns
            commands = [
                "gnome-screensaver-command -l",  # GNOME
                "xdg-screensaver lock",           # XDG
                "loginctl lock-session",          # systemd
                "xlock",                          # XLock
                "slock"                           # Simple lock
            ]
            
            for cmd in commands:
                try:
                    subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
                    return True
                except:
                    continue
                    
            print("[EMERGENCY] Não foi possível encontrar comando de bloqueio no Linux")
            return False
            
        elif system == "Darwin":  # macOS
            subprocess.run("pmset displaysleepnow", shell=True)
            return True
            
        else:
            print(f"[EMERGENCY] Sistema não suportado: {system}")
            return False
            
    except Exception as e:
        print(f"[EMERGENCY] Erro ao bloquear usuário: {e}")
        return False

# ============================================================================
# INTERFACE DE COMANDOS
# ============================================================================

def emergency_menu():
    """Menu interativo para funções de emergência."""
    collapser = SystemCollapser()
    remote_server = None
    
    while True:
        print("\n" + "="*60)
        print("MENU DE EMERGÊNCIA - SISTEMA DE PERÍCIA")
        print("="*60)
        print("1. Desligamento programado (X minutos)")
        print("2. Desligamento imediato")
        print("3. Cancelar desligamento programado")
        print("4. Iniciar colapso do sistema (CPU+RAM+Disco)")
        print("5. Parar colapso do sistema")
        print("6. Limpar logs sensíveis")
        print("7. Bloquear sessão do usuário")
        print("8. Iniciar servidor de controle remoto")
        print("9. Parar servidor de controle remoto")
        print("0. Sair")
        print("="*60)
        
        try:
            choice = input("Escolha uma opção: ").strip()
            
            if choice == "1":
                minutes = int(input("Minutos até desligamento: "))
                schedule_shutdown(minutes)
                print(f"[EMERGENCY] Desligamento programado para {minutes} minutos")
                
            elif choice == "2":
                confirm = input("Desligar imediatamente? (s/n): ").lower()
                if confirm == 's':
                    shutdown_system()
                    
            elif choice == "3":
                if cancel_scheduled_shutdown():
                    print("[EMERGENCY] Desligamento cancelado")
                else:
                    print("[EMERGENCY] Não há desligamento programado ou erro ao cancelar")
                    
            elif choice == "4":
                seconds = int(input("Duração do colapso (segundos, máx 600): "))
                if seconds > 600:
                    seconds = 600
                collapser.start_full_collapse(seconds)
                
            elif choice == "5":
                collapser.stop_collapse()
                
            elif choice == "6":
                confirm = input("Limpar logs sensíveis? (s/n): ").lower()
                if confirm == 's':
                    count = clean_sensitive_logs()
                    print(f"[EMERGENCY] {count} arquivos de log removidos")
                    
            elif choice == "7":
                lock_current_user()
                print("[EMERGENCY] Sessão bloqueada")
                
            elif choice == "8":
                port = int(input("Porta do servidor (padrão 8080): ") or "8080")
                remote_server = RemoteControlServer(port=port, password_hash=EMERGENCY_PASSWORD_HASH)
                if remote_server.start():
                   print("[EMERGENCY] Servidor iniciado")
                   print("[EMERGENCY] Lembrete: use ?cmd=status|shutdown|cancel&auth=SEU_HASH_SHA256")
                else:
                   print("[EMERGENCY] Falha ao iniciar servidor")
        
            elif choice == "9":
                if remote_server:
                    remote_server.stop()
                    remote_server = None
                    print("[EMERGENCY] Servidor parado")
                else:
                    print("[EMERGENCY] Servidor não está em execução")
        
            elif choice == "0":
                if collapser.running:
                    collapser.stop_collapse()
                if remote_server and remote_server.running:
                    remote_server.stop()
                print("[EMERGENCY] Saindo do menu de emergência")
                break
    
            else:
                print("[EMERGENCY] Opção inválida")
                
        except ValueError:
            print("[EMERGENCY] Entrada inválida")
        except KeyboardInterrupt:
            print("\n[EMERGENCY] Interrompido pelo usuário")
            break
        except Exception as e:
            print(f"[EMERGENCY] Erro: {e}")

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("MÓDULO DE EMERGÊNCIA - SISTEMA DE PERÍCIA")
    print("="*60)
    print("ATENÇÃO: Estas funções podem causar perda de dados")
    print("e tornar o sistema inoperante. Use com responsabilidade.")
    print("="*60)
    
    emergency_menu()