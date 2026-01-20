#!/usr/bin/env python3
"""
PurmaLinux AI Agent
Ejecuta acciones del modelo de IA de forma segura dentro del directorio del usuario.
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Optional, Tuple
import requests

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("PURMA_MODEL", "purma")
HOME = Path.home()
WORK_DIR = HOME / "AI"
MAX_OUTPUT_LENGTH = 10000

# Ensure work directory exists
WORK_DIR.mkdir(exist_ok=True)


class SecurityError(Exception):
    """Raised when a security violation is detected"""
    pass


def is_path_safe(path: str) -> bool:
    """Check if path is within user's home directory"""
    try:
        resolved = Path(path).resolve()
        return str(resolved).startswith(str(HOME))
    except Exception:
        return False


def sanitize_command(command: str) -> Tuple[bool, str]:
    """
    Check if command is safe to execute.
    Returns (is_safe, reason)
    """
    # Blocked commands/patterns
    blocked_patterns = [
        r'\bsudo\b',
        r'\bsu\b',
        r'\brm\s+-rf\s+/',
        r'\bdd\b.*of=',
        r'\bmkfs\b',
        r'\bfdisk\b',
        r'\bparted\b',
        r'>\s*/etc/',
        r'>\s*/usr/',
        r'>\s*/var/',
        r'>\s*/boot/',
        r'\bchmod\s+777\s+/',
        r'\bchown\b.*/',
        r'\bsystemctl\b',
        r'\bservice\b',
        r'\breboot\b',
        r'\bshutdown\b',
        r'\binit\b',
        r':(){ :|:& };:',  # Fork bomb
        r'\beval\b.*\$',
        r'\bcurl\b.*\|\s*(ba)?sh',
        r'\bwget\b.*\|\s*(ba)?sh',
    ]

    for pattern in blocked_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Comando bloqueado: patrón '{pattern}' detectado"

    # Check for path traversal outside home
    if '..' in command:
        # Simple check - could be more sophisticated
        pass

    return True, "OK"


def execute_command(command: str, cwd: Optional[str] = None) -> dict:
    """Execute a shell command safely"""
    # Security check
    is_safe, reason = sanitize_command(command)
    if not is_safe:
        return {
            "success": False,
            "error": f"Seguridad: {reason}",
            "output": ""
        }

    # Set working directory
    work_dir = cwd if cwd and is_path_safe(cwd) else str(WORK_DIR)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
            env={
                **os.environ,
                "HOME": str(HOME),
                "USER": os.getenv("USER", "purma"),
            }
        )

        output = result.stdout + result.stderr
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... (output truncated)"

        return {
            "success": result.returncode == 0,
            "output": output,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout: comando excedió 60 segundos",
            "output": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": ""
        }


def read_file(path: str) -> dict:
    """Read a file safely"""
    if not is_path_safe(path):
        return {
            "success": False,
            "error": f"Acceso denegado: {path} está fuera del directorio home"
        }

    try:
        file_path = Path(path).expanduser().resolve()
        content = file_path.read_text()

        if len(content) > MAX_OUTPUT_LENGTH:
            content = content[:MAX_OUTPUT_LENGTH] + "\n... (content truncated)"

        return {
            "success": True,
            "content": content
        }
    except FileNotFoundError:
        return {"success": False, "error": f"Archivo no encontrado: {path}"}
    except PermissionError:
        return {"success": False, "error": f"Permiso denegado: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write to a file safely"""
    if not is_path_safe(path):
        return {
            "success": False,
            "error": f"Acceso denegado: {path} está fuera del directorio home"
        }

    try:
        file_path = Path(path).expanduser().resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

        return {
            "success": True,
            "message": f"Archivo escrito: {path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(path: str, confirm: bool = False) -> dict:
    """Delete a file safely (requires confirmation)"""
    if not confirm:
        return {
            "success": False,
            "requires_confirmation": True,
            "message": f"¿Confirmas eliminar {path}? (requiere confirm=True)"
        }

    if not is_path_safe(path):
        return {
            "success": False,
            "error": f"Acceso denegado: {path} está fuera del directorio home"
        }

    try:
        file_path = Path(path).expanduser().resolve()
        if file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
        else:
            file_path.unlink()

        return {
            "success": True,
            "message": f"Eliminado: {path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_directory(path: str = "~") -> dict:
    """List directory contents"""
    expanded_path = Path(path).expanduser().resolve()

    if not is_path_safe(str(expanded_path)):
        return {
            "success": False,
            "error": f"Acceso denegado: {path} está fuera del directorio home"
        }

    try:
        items = []
        for item in expanded_path.iterdir():
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })

        return {
            "success": True,
            "path": str(expanded_path),
            "items": sorted(items, key=lambda x: (x["type"] != "dir", x["name"]))
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def chat_with_ollama(message: str, history: list = None) -> str:
    """Send message to Ollama and get response"""
    messages = history or []
    messages.append({"role": "user", "content": message})

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error conectando con Ollama: {e}"


# Available tools for the agent
TOOLS = {
    "execute": execute_command,
    "read": read_file,
    "write": write_file,
    "delete": delete_file,
    "list": list_directory,
}


def main():
    """Main entry point for CLI usage"""
    if len(sys.argv) > 1:
        # Direct command mode
        message = " ".join(sys.argv[1:])
        response = chat_with_ollama(message)
        print(response)
    else:
        # Interactive mode
        print("Purma AI Agent")
        print("Escribe 'salir' para terminar\n")

        history = []

        while True:
            try:
                user_input = input("tú: ").strip()
                if user_input.lower() in ["salir", "exit", "quit"]:
                    break
                if not user_input:
                    continue

                response = chat_with_ollama(user_input, history)
                print(f"\npurma: {response}\n")

                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response})

            except KeyboardInterrupt:
                print("\n\nHasta luego!")
                break
            except EOFError:
                break


if __name__ == "__main__":
    main()
