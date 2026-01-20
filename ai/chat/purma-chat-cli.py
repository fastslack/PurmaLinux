#!/usr/bin/env python3
"""
PurmaLinux - Terminal Chat Client
Cliente de chat para terminal que conecta con el servidor Purma.
"""

import os
import sys
import json
import requests
from typing import Optional

# Configuration
PURMA_SERVER = os.getenv("PURMA_SERVER", "http://127.0.0.1:11435")

# Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def print_header():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  {Colors.BOLD}░█▀█░█░█░█▀▄░█▄█░█▀█{Colors.ENDC}{Colors.CYAN}                                       ║
║  {Colors.BOLD}░█▀▀░█░█░█▀▄░█░█░█▀█{Colors.ENDC}{Colors.CYAN}    AI Assistant                       ║
║  {Colors.BOLD}░▀░░░▀▀▀░▀░▀░▀░▀░▀░▀{Colors.ENDC}{Colors.CYAN}                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}
""")

def print_help():
    print(f"""
{Colors.YELLOW}Comandos especiales:{Colors.ENDC}
  {Colors.CYAN}/help{Colors.ENDC}     - Mostrar esta ayuda
  {Colors.CYAN}/clear{Colors.ENDC}    - Limpiar historial
  {Colors.CYAN}/status{Colors.ENDC}   - Estado del servidor
  {Colors.CYAN}/models{Colors.ENDC}   - Listar modelos disponibles
  {Colors.CYAN}/model X{Colors.ENDC}  - Cambiar modelo
  {Colors.CYAN}/ls [dir]{Colors.ENDC} - Listar directorio
  {Colors.CYAN}/run cmd{Colors.ENDC}  - Ejecutar comando directamente
  {Colors.CYAN}/exit{Colors.ENDC}     - Salir

{Colors.DIM}Escribe cualquier cosa para chatear con Purma AI.{Colors.ENDC}
""")

def check_server() -> bool:
    """Check if server is running"""
    try:
        response = requests.get(f"{PURMA_SERVER}/status", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_status():
    """Get server status"""
    try:
        response = requests.get(f"{PURMA_SERVER}/status", timeout=10)
        data = response.json()
        print(f"""
{Colors.CYAN}Estado del servidor:{Colors.ENDC}
  Status:   {Colors.GREEN if data['status'] == 'running' else Colors.RED}{data['status']}{Colors.ENDC}
  Ollama:   {Colors.GREEN if data['ollama_connected'] else Colors.RED}{'Conectado' if data['ollama_connected'] else 'Desconectado'}{Colors.ENDC}
  Modelo:   {data['default_model']}
  Modelos:  {', '.join(data['models'][:5])}{'...' if len(data['models']) > 5 else ''}
""")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def get_models():
    """List available models"""
    try:
        response = requests.get(f"{PURMA_SERVER}/models", timeout=10)
        data = response.json()
        print(f"\n{Colors.CYAN}Modelos disponibles:{Colors.ENDC}")
        for model in data['models']:
            marker = "→" if model == data['default'] else " "
            print(f"  {marker} {model}")
        print()
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def list_directory(path: str = "~"):
    """List directory contents"""
    try:
        response = requests.get(f"{PURMA_SERVER}/ls", params={"path": path}, timeout=10)
        data = response.json()

        if not data.get("success", True):
            print(f"{Colors.RED}Error: {data.get('error', 'Unknown error')}{Colors.ENDC}")
            return

        print(f"\n{Colors.CYAN}Contenido de {data['path']}:{Colors.ENDC}\n")

        for item in data['items']:
            if item['type'] == 'dir':
                print(f"  {Colors.BLUE}📁 {item['name']}/{Colors.ENDC}")
            else:
                size = item.get('size', 0)
                size_str = f"{size:,}" if size else "0"
                print(f"  📄 {item['name']} {Colors.DIM}({size_str} bytes){Colors.ENDC}")
        print()
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def run_command(command: str):
    """Execute a command directly"""
    try:
        response = requests.post(
            f"{PURMA_SERVER}/execute",
            params={"command": command},
            timeout=60
        )
        data = response.json()

        if data.get("success"):
            print(f"\n{Colors.GREEN}✓ Comando ejecutado{Colors.ENDC}")
            if data.get("output"):
                print(f"{Colors.DIM}{data['output']}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}✗ Error: {data.get('error', 'Unknown')}{Colors.ENDC}")
            if data.get("output"):
                print(f"{Colors.DIM}{data['output']}{Colors.ENDC}")
        print()
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def chat(message: str, history: list, model: Optional[str] = None) -> Optional[dict]:
    """Send a chat message"""
    try:
        response = requests.post(
            f"{PURMA_SERVER}/chat",
            json={
                "message": message,
                "history": history,
                "model": model,
                "execute_actions": True
            },
            timeout=120
        )
        return response.json()
    except requests.exceptions.Timeout:
        print(f"{Colors.RED}Error: Timeout esperando respuesta{Colors.ENDC}")
        return None
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
        return None

def format_response(response: dict):
    """Format and print the AI response"""
    print(f"\n{Colors.CYAN}purma:{Colors.ENDC} {response['response']}")

    # Show executed actions
    if response.get('actions'):
        print(f"\n{Colors.YELLOW}Acciones ejecutadas:{Colors.ENDC}")
        for action in response['actions']:
            status = f"{Colors.GREEN}✓{Colors.ENDC}" if action['success'] else f"{Colors.RED}✗{Colors.ENDC}"
            print(f"  {status} {action['type']}: {action['description']}")
            if action.get('output') and len(action['output']) < 200:
                print(f"     {Colors.DIM}{action['output'][:200]}{Colors.ENDC}")
            if action.get('error'):
                print(f"     {Colors.RED}{action['error']}{Colors.ENDC}")

    print()

def main():
    print_header()

    # Check server
    if not check_server():
        print(f"{Colors.RED}Error: No se puede conectar con el servidor Purma{Colors.ENDC}")
        print(f"{Colors.DIM}Asegúrate de que el servidor esté corriendo:")
        print(f"  purma-server start{Colors.ENDC}\n")
        sys.exit(1)

    print(f"{Colors.GREEN}Conectado al servidor Purma{Colors.ENDC}")
    print(f"{Colors.DIM}Escribe /help para ver comandos disponibles{Colors.ENDC}\n")

    history = []
    current_model = None

    while True:
        try:
            user_input = input(f"{Colors.GREEN}tú:{Colors.ENDC} ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd in ["/exit", "/quit", "/q"]:
                    print(f"\n{Colors.CYAN}¡Hasta luego!{Colors.ENDC}\n")
                    break
                elif cmd == "/help":
                    print_help()
                elif cmd == "/clear":
                    history = []
                    print(f"{Colors.GREEN}Historial limpiado{Colors.ENDC}\n")
                elif cmd == "/status":
                    get_status()
                elif cmd == "/models":
                    get_models()
                elif cmd == "/model":
                    if arg:
                        current_model = arg
                        print(f"{Colors.GREEN}Modelo cambiado a: {arg}{Colors.ENDC}\n")
                    else:
                        print(f"{Colors.YELLOW}Uso: /model <nombre>{Colors.ENDC}\n")
                elif cmd == "/ls":
                    list_directory(arg or "~")
                elif cmd == "/run":
                    if arg:
                        run_command(arg)
                    else:
                        print(f"{Colors.YELLOW}Uso: /run <comando>{Colors.ENDC}\n")
                else:
                    print(f"{Colors.YELLOW}Comando desconocido: {cmd}{Colors.ENDC}\n")
                continue

            # Send chat message
            response = chat(user_input, history, current_model)

            if response:
                format_response(response)

                # Update history
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response['response']})

                # Keep history manageable
                if len(history) > 20:
                    history = history[-20:]

        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}¡Hasta luego!{Colors.ENDC}\n")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
