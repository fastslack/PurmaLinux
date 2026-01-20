#!/usr/bin/env python3
"""
PurmaLinux Flow Recorder Daemon
Captures user actions for Flow automation

Captures:
- Terminal commands (via shell wrapper)
- Clipboard changes
- File operations (via inotify)
- Window focus changes
- Keyboard shortcuts (optional)
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx


# ============================================
# Configuration
# ============================================

PURMA_SERVER = "http://localhost:8787"
CLIPBOARD_CHECK_INTERVAL = 0.5
SOCKET_PATH = Path.home() / ".config" / "purma" / "flow_recorder.sock"
LOG_FILE = Path.home() / ".config" / "purma" / "flow_recorder.log"

SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)


# ============================================
# Logging
# ============================================

def log(message: str):
    """Log a message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except Exception:
        pass


# ============================================
# Recorder State
# ============================================

class RecorderState:
    """Global recorder state"""
    def __init__(self):
        self.recording = False
        self.recording_id: Optional[str] = None
        self.last_clipboard = ""
        self.last_window = ""
        self.action_count = 0
        self.start_time: Optional[float] = None


state = RecorderState()


# ============================================
# API Client
# ============================================

async def call_api(method: str, endpoint: str, data: dict = None) -> dict:
    """Call Purma server API"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{PURMA_SERVER}{endpoint}"
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=data or {})
            else:
                return {"error": f"Unknown method: {method}"}

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


async def send_action(action_type: str, data: dict, window: str = "", working_dir: str = ""):
    """Send a recorded action to the server"""
    if not state.recording:
        return

    action = {
        "type": action_type,
        "data": data,
        "window_title": window or state.last_window,
        "working_dir": working_dir or os.getcwd(),
        "timestamp": time.time(),
    }

    result = await call_api("POST", "/flow/record/action", action)

    if "error" not in result:
        state.action_count += 1
        log(f"Recorded action #{state.action_count}: {action_type}")

    return result


# ============================================
# Clipboard Watcher
# ============================================

async def get_clipboard() -> str:
    """Get current clipboard content"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "xclip", "-selection", "clipboard", "-o",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode('utf-8', errors='ignore')
    except Exception:
        return ""


async def watch_clipboard():
    """Watch clipboard for changes"""
    log("Starting clipboard watcher")
    state.last_clipboard = await get_clipboard()

    while True:
        await asyncio.sleep(CLIPBOARD_CHECK_INTERVAL)

        if not state.recording:
            continue

        try:
            current = await get_clipboard()
            if current and current != state.last_clipboard:
                await send_action("clipboard", {
                    "content": current[:500],
                    "action": "copy",
                    "length": len(current),
                })
                state.last_clipboard = current
        except Exception as e:
            log(f"Clipboard watch error: {e}")


# ============================================
# Window Watcher
# ============================================

async def get_active_window() -> tuple:
    """Get active window title and class"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "xdotool", "getactivewindow",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        window_id = stdout.decode().strip()

        if not window_id:
            return "", ""

        proc = await asyncio.create_subprocess_exec(
            "xdotool", "getwindowname", window_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        window_name = stdout.decode().strip()

        proc = await asyncio.create_subprocess_exec(
            "xprop", "-id", window_id, "WM_CLASS",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        class_line = stdout.decode().strip()
        window_class = ""
        if "=" in class_line:
            window_class = class_line.split("=")[1].strip().strip('"').split(",")[0].strip().strip('"')

        return window_name, window_class

    except Exception:
        return "", ""


async def watch_windows():
    """Watch for window focus changes"""
    log("Starting window watcher")
    state.last_window, _ = await get_active_window()

    while True:
        await asyncio.sleep(0.5)

        if not state.recording:
            continue

        try:
            current_name, current_class = await get_active_window()

            if current_name and current_name != state.last_window:
                await send_action("window_focus", {
                    "window_title": current_name,
                    "window_class": current_class,
                    "previous_window": state.last_window,
                })
                state.last_window = current_name

        except Exception as e:
            log(f"Window watch error: {e}")


# ============================================
# Command Recorder (Shell Integration)
# ============================================

async def handle_command_record(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle incoming command records from shell wrapper"""
    try:
        data = await reader.read(4096)
        if data:
            message = json.loads(data.decode())

            if message.get("type") == "command" and state.recording:
                await send_action("command", {
                    "command": message.get("command", ""),
                    "exit_code": message.get("exit_code", 0),
                    "output": message.get("output", "")[:1000],
                    "duration": message.get("duration", 0),
                }, working_dir=message.get("cwd", ""))

            writer.write(b'{"status": "ok"}')
            await writer.drain()

    except Exception as e:
        log(f"Command handler error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_command_server():
    """Start Unix socket server for command recording"""
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()

    log(f"Starting command server on {SOCKET_PATH}")
    server = await asyncio.start_unix_server(
        handle_command_record,
        path=str(SOCKET_PATH)
    )

    async with server:
        await server.serve_forever()


# ============================================
# Control API
# ============================================

async def start_recording(name: str = "") -> dict:
    """Start a new recording session"""
    if state.recording:
        return {"error": "Already recording"}

    result = await call_api("POST", "/flow/recording/start", {"name": name})

    if "error" not in result:
        state.recording = True
        state.recording_id = result.get("recording", {}).get("id")
        state.action_count = 0
        state.start_time = time.time()
        state.last_clipboard = await get_clipboard()
        state.last_window, _ = await get_active_window()

        log(f"Started recording: {state.recording_id}")

        subprocess.Popen([
            "notify-send", "-i", "media-record",
            "Purma Flow", "Grabacion iniciada"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return result


async def stop_recording() -> dict:
    """Stop current recording"""
    if not state.recording:
        return {"error": "Not recording"}

    result = await call_api("POST", "/flow/recording/stop", {})

    if "error" not in result:
        duration = time.time() - (state.start_time or 0)
        log(f"Stopped recording: {state.recording_id} ({state.action_count} actions, {duration:.1f}s)")

        state.recording = False
        state.recording_id = None

        subprocess.Popen([
            "notify-send", "-i", "media-playback-stop",
            "Purma Flow",
            f"Grabacion terminada: {state.action_count} acciones"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return result


async def get_status() -> dict:
    """Get recorder status"""
    return {
        "recording": state.recording,
        "recording_id": state.recording_id,
        "action_count": state.action_count,
        "duration": time.time() - state.start_time if state.start_time else 0,
        "last_window": state.last_window,
    }


# ============================================
# HTTP Control Server
# ============================================

async def handle_control_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle HTTP-like control requests"""
    try:
        data = await reader.read(1024)
        request = data.decode()

        lines = request.split('\r\n')
        if not lines:
            return

        first_line = lines[0]
        parts = first_line.split(' ')
        if len(parts) < 2:
            return

        method, path = parts[0], parts[1]

        if path == "/start" and method == "POST":
            result = await start_recording()
        elif path == "/stop" and method == "POST":
            result = await stop_recording()
        elif path == "/status" and method == "GET":
            result = await get_status()
        elif path == "/toggle" and method == "POST":
            if state.recording:
                result = await stop_recording()
            else:
                result = await start_recording()
        else:
            result = {"error": "Unknown endpoint"}

        response_body = json.dumps(result)
        response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"

        writer.write(response.encode())
        await writer.drain()

    except Exception as e:
        log(f"Control request error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_control_server(port: int = 8790):
    """Start HTTP control server"""
    log(f"Starting control server on port {port}")
    server = await asyncio.start_server(
        handle_control_request,
        "127.0.0.1",
        port
    )

    async with server:
        await server.serve_forever()


# ============================================
# Main
# ============================================

async def main():
    """Main entry point"""
    log("=" * 50)
    log("Purma Flow Recorder starting...")

    def signal_handler(sig, frame):
        log("Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    tasks = [
        asyncio.create_task(watch_clipboard()),
        asyncio.create_task(watch_windows()),
        asyncio.create_task(start_command_server()),
        asyncio.create_task(start_control_server()),
    ]

    log("Recorder ready. Watchers started.")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
