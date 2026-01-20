"""
PurmaLinux Flow - Automation by Demonstration
=============================================
Author: Matías Aguirre
Company: Matware

"Show Purma what you want and it will repeat it forever"

Uses local AI models (Ollama) as primary engine, with optional
remote providers as fallback for complex tasks.
"""

import asyncio
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import yaml


# ============================================
# Configuration
# ============================================

FLOW_CONFIG_DIR = Path.home() / ".config" / "purma" / "flows"
FLOW_RECORDINGS_DIR = Path.home() / ".config" / "purma" / "flow_recordings"
FLOW_STATE_FILE = Path.home() / ".config" / "purma" / "flow_state.json"

FLOW_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
FLOW_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# Enums
# ============================================

class ActionType(str, Enum):
    """Types of recordable actions"""
    COMMAND = "command"           # Terminal command
    KEYBOARD = "keyboard"         # Keyboard input/shortcut
    MOUSE_CLICK = "mouse_click"   # Mouse click
    MOUSE_DRAG = "mouse_drag"     # Mouse drag
    CLIPBOARD = "clipboard"       # Clipboard copy/paste
    FILE_OPEN = "file_open"       # File opened
    FILE_SAVE = "file_save"       # File saved
    FILE_CREATE = "file_create"   # File created
    FILE_DELETE = "file_delete"   # File deleted
    APP_LAUNCH = "app_launch"     # Application launched
    APP_CLOSE = "app_close"       # Application closed
    WINDOW_FOCUS = "window_focus" # Window focus changed
    URL_OPEN = "url_open"         # URL opened in browser
    CUSTOM = "custom"             # Custom action


class TriggerType(str, Enum):
    """Types of workflow triggers"""
    MANUAL = "manual"             # User manually triggers
    FILE_PATTERN = "file_pattern" # File matching pattern opened/created
    TIME_SCHEDULE = "time_schedule"  # Scheduled time
    APP_LAUNCH = "app_launch"     # When app is launched
    COMMAND_PATTERN = "command_pattern"  # Command matching pattern
    CLIPBOARD_PATTERN = "clipboard_pattern"  # Clipboard content matches
    HOTKEY = "hotkey"             # Keyboard shortcut
    DIRECTORY_WATCH = "directory_watch"  # File changes in directory
    WEBHOOK = "webhook"           # External webhook call
    VOICE = "voice"               # Voice command (future)


class FlowStatus(str, Enum):
    """Flow execution status"""
    IDLE = "idle"
    RECORDING = "recording"
    ANALYZING = "analyzing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


# ============================================
# Data Models
# ============================================

@dataclass
class RecordedAction:
    """A single recorded action"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: ActionType = ActionType.COMMAND
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    window_class: str = ""
    window_title: str = ""
    working_dir: str = ""

    # Metadata added by AI analysis
    intent: str = ""              # What the user intended
    is_variable: bool = False     # Can this change between runs?
    variable_name: str = ""       # Name of variable if variable
    dependencies: List[str] = field(default_factory=list)


@dataclass
class FlowStep:
    """A step in a workflow (processed action)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: ActionType = ActionType.COMMAND
    description: str = ""
    command: str = ""             # For command actions
    template: str = ""            # Command template with variables
    variables: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict] = field(default_factory=list)  # When to skip
    on_error: str = "stop"        # stop, continue, retry
    timeout: int = 30             # Seconds
    wait_after: float = 0.5       # Seconds to wait after action

    # For UI actions
    target_window: str = ""
    coordinates: Optional[tuple] = None
    keystrokes: str = ""


@dataclass
class FlowTrigger:
    """A trigger that starts a flow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: TriggerType = TriggerType.MANUAL
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Flow:
    """A complete workflow definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    icon: str = "⚡"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # The workflow
    steps: List[FlowStep] = field(default_factory=list)
    triggers: List[FlowTrigger] = field(default_factory=list)

    # Variables that can be customized
    variables: Dict[str, Any] = field(default_factory=dict)
    variable_prompts: Dict[str, str] = field(default_factory=dict)

    # Settings
    enabled: bool = True
    run_count: int = 0
    last_run: Optional[str] = None
    avg_duration: float = 0.0

    # AI metadata
    ai_summary: str = ""
    ai_suggestions: List[str] = field(default_factory=list)
    original_recording_id: Optional[str] = None

    # Tags for organization
    tags: List[str] = field(default_factory=list)


@dataclass
class Recording:
    """A recording session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    actions: List[RecordedAction] = field(default_factory=list)
    status: FlowStatus = FlowStatus.RECORDING

    # Context at start of recording
    initial_window: str = ""
    initial_directory: str = ""

    # AI analysis results
    analyzed: bool = False
    detected_intent: str = ""
    detected_patterns: List[Dict] = field(default_factory=list)
    suggested_triggers: List[Dict] = field(default_factory=list)
    generated_flow_id: Optional[str] = None


@dataclass
class FlowState:
    """Global flow system state"""
    active_recording: Optional[str] = None
    running_flows: List[str] = field(default_factory=list)
    enabled_triggers: Dict[str, List[str]] = field(default_factory=dict)
    last_clipboard: str = ""


# ============================================
# Flow Manager
# ============================================

class FlowManager:
    """Manages flows, recordings, and execution"""

    def __init__(self):
        self.flows: Dict[str, Flow] = {}
        self.recordings: Dict[str, Recording] = {}
        self.state = FlowState()
        self.action_handlers: Dict[ActionType, Callable] = {}
        self._setup_handlers()
        self._load_flows()
        self._load_state()

    def _setup_handlers(self):
        """Setup action execution handlers"""
        self.action_handlers = {
            ActionType.COMMAND: self._execute_command,
            ActionType.KEYBOARD: self._execute_keyboard,
            ActionType.MOUSE_CLICK: self._execute_click,
            ActionType.APP_LAUNCH: self._execute_app_launch,
            ActionType.FILE_OPEN: self._execute_file_open,
            ActionType.CLIPBOARD: self._execute_clipboard,
        }

    def _load_flows(self):
        """Load all flows from config directory"""
        for flow_file in FLOW_CONFIG_DIR.glob("*.yaml"):
            try:
                with open(flow_file) as f:
                    data = yaml.safe_load(f)
                    flow = self._dict_to_flow(data)
                    self.flows[flow.id] = flow
            except Exception as e:
                print(f"Error loading flow {flow_file}: {e}")

        for flow_file in FLOW_CONFIG_DIR.glob("*.json"):
            try:
                with open(flow_file) as f:
                    data = json.load(f)
                    flow = self._dict_to_flow(data)
                    self.flows[flow.id] = flow
            except Exception as e:
                print(f"Error loading flow {flow_file}: {e}")

    def _load_state(self):
        """Load global state"""
        if FLOW_STATE_FILE.exists():
            try:
                with open(FLOW_STATE_FILE) as f:
                    data = json.load(f)
                    self.state = FlowState(**data)
            except Exception:
                self.state = FlowState()

    def _save_state(self):
        """Save global state"""
        with open(FLOW_STATE_FILE, 'w') as f:
            json.dump(asdict(self.state), f, indent=2)

    def _save_flow(self, flow: Flow):
        """Save a flow to disk"""
        flow_file = FLOW_CONFIG_DIR / f"{flow.id}.yaml"
        with open(flow_file, 'w') as f:
            yaml.dump(self._flow_to_dict(flow), f, default_flow_style=False)

    def _save_recording(self, recording: Recording):
        """Save a recording to disk"""
        rec_file = FLOW_RECORDINGS_DIR / f"{recording.id}.json"
        with open(rec_file, 'w') as f:
            json.dump(self._recording_to_dict(recording), f, indent=2)

    def _flow_to_dict(self, flow: Flow) -> Dict:
        """Convert Flow to dict for serialization"""
        d = asdict(flow)
        d['steps'] = [asdict(s) if isinstance(s, FlowStep) else s for s in flow.steps]
        d['triggers'] = [asdict(t) if isinstance(t, FlowTrigger) else t for t in flow.triggers]
        return d

    def _dict_to_flow(self, data: Dict) -> Flow:
        """Convert dict to Flow"""
        steps = [FlowStep(**s) if isinstance(s, dict) else s for s in data.get('steps', [])]
        triggers = [FlowTrigger(**t) if isinstance(t, dict) else t for t in data.get('triggers', [])]
        data['steps'] = steps
        data['triggers'] = triggers
        return Flow(**data)

    def _recording_to_dict(self, rec: Recording) -> Dict:
        """Convert Recording to dict"""
        d = asdict(rec)
        d['actions'] = [asdict(a) if isinstance(a, RecordedAction) else a for a in rec.actions]
        return d

    # ============================================
    # Recording API
    # ============================================

    def start_recording(self, name: str = "") -> Recording:
        """Start a new recording session"""
        if self.state.active_recording:
            raise ValueError("Already recording. Stop current recording first.")

        recording = Recording(
            name=name or f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            initial_directory=os.getcwd(),
        )

        # Get active window
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            recording.initial_window = result.stdout.strip()
        except Exception:
            pass

        self.recordings[recording.id] = recording
        self.state.active_recording = recording.id
        self._save_state()

        return recording

    def stop_recording(self) -> Optional[Recording]:
        """Stop current recording"""
        if not self.state.active_recording:
            return None

        recording = self.recordings.get(self.state.active_recording)
        if recording:
            recording.ended_at = datetime.now().isoformat()
            recording.status = FlowStatus.IDLE
            self._save_recording(recording)

        self.state.active_recording = None
        self._save_state()

        return recording

    def add_action(self, action: RecordedAction) -> bool:
        """Add an action to current recording"""
        if not self.state.active_recording:
            return False

        recording = self.recordings.get(self.state.active_recording)
        if recording:
            recording.actions.append(action)
            return True
        return False

    def record_command(self, command: str, output: str = "", exit_code: int = 0,
                       working_dir: str = "") -> bool:
        """Record a terminal command"""
        action = RecordedAction(
            type=ActionType.COMMAND,
            data={
                "command": command,
                "output": output[:1000],
                "exit_code": exit_code,
            },
            working_dir=working_dir or os.getcwd(),
        )
        return self.add_action(action)

    def record_file_action(self, action_type: ActionType, path: str,
                           extra_data: Dict = None) -> bool:
        """Record a file action"""
        action = RecordedAction(
            type=action_type,
            data={
                "path": path,
                "filename": os.path.basename(path),
                "extension": os.path.splitext(path)[1],
                **(extra_data or {})
            },
            working_dir=os.path.dirname(path),
        )
        return self.add_action(action)

    def record_clipboard(self, content: str, action: str = "copy") -> bool:
        """Record clipboard action"""
        rec_action = RecordedAction(
            type=ActionType.CLIPBOARD,
            data={
                "content": content[:500],
                "action": action,
                "content_type": self._detect_content_type(content),
            }
        )
        self.state.last_clipboard = content
        return self.add_action(rec_action)

    def _detect_content_type(self, content: str) -> str:
        """Detect type of clipboard content"""
        content = content.strip()

        if content.startswith(('http://', 'https://')):
            return "url"
        if content.startswith('/') or content.startswith('~'):
            return "path"
        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', content):
            return "email"
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', content):
            return "ip"
        if '\n' in content and ('{' in content or 'def ' in content or 'function' in content):
            return "code"
        if '\n' in content:
            return "multiline"
        return "text"

    # ============================================
    # Flow CRUD
    # ============================================

    def create_flow(self, name: str, description: str = "", steps: List[FlowStep] = None) -> Flow:
        """Create a new flow"""
        flow = Flow(
            name=name,
            description=description,
            steps=steps or [],
        )
        self.flows[flow.id] = flow
        self._save_flow(flow)
        return flow

    def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a flow by ID"""
        return self.flows.get(flow_id)

    def update_flow(self, flow_id: str, updates: Dict) -> Optional[Flow]:
        """Update a flow"""
        flow = self.flows.get(flow_id)
        if not flow:
            return None

        for key, value in updates.items():
            if hasattr(flow, key):
                setattr(flow, key, value)

        flow.updated_at = datetime.now().isoformat()
        self._save_flow(flow)
        return flow

    def delete_flow(self, flow_id: str) -> bool:
        """Delete a flow"""
        if flow_id not in self.flows:
            return False

        del self.flows[flow_id]
        flow_file = FLOW_CONFIG_DIR / f"{flow_id}.yaml"
        if flow_file.exists():
            flow_file.unlink()

        return True

    def list_flows(self) -> List[Dict]:
        """List all flows"""
        return [
            {
                "id": f.id,
                "name": f.name,
                "description": f.description,
                "icon": f.icon,
                "enabled": f.enabled,
                "steps_count": len(f.steps),
                "triggers_count": len(f.triggers),
                "run_count": f.run_count,
                "last_run": f.last_run,
                "tags": f.tags,
            }
            for f in self.flows.values()
        ]

    # ============================================
    # Flow Execution
    # ============================================

    async def run_flow(self, flow_id: str, variables: Dict = None,
                       dry_run: bool = False) -> Dict:
        """Execute a flow"""
        flow = self.flows.get(flow_id)
        if not flow:
            return {"success": False, "error": "Flow not found"}

        if not flow.enabled and not dry_run:
            return {"success": False, "error": "Flow is disabled"}

        run_vars = {**flow.variables, **(variables or {})}

        results = []
        start_time = time.time()

        self.state.running_flows.append(flow_id)
        self._save_state()

        try:
            for i, step in enumerate(flow.steps):
                step_result = {
                    "step": i + 1,
                    "description": step.description,
                    "action_type": step.action_type,
                    "success": False,
                }

                if step.conditions and not self._check_conditions(step.conditions, run_vars):
                    step_result["skipped"] = True
                    step_result["success"] = True
                    results.append(step_result)
                    continue

                if dry_run:
                    step_result["dry_run"] = True
                    step_result["would_execute"] = self._render_command(step, run_vars)
                    step_result["success"] = True
                else:
                    try:
                        output = await self._execute_step(step, run_vars)
                        step_result["success"] = True
                        step_result["output"] = output
                    except Exception as e:
                        step_result["error"] = str(e)
                        if step.on_error == "stop":
                            results.append(step_result)
                            break

                results.append(step_result)

                if step.wait_after > 0 and not dry_run:
                    await asyncio.sleep(step.wait_after)

            duration = time.time() - start_time

            if not dry_run:
                flow.run_count += 1
                flow.last_run = datetime.now().isoformat()
                flow.avg_duration = (flow.avg_duration * (flow.run_count - 1) + duration) / flow.run_count
                self._save_flow(flow)

            success = all(r.get("success", False) for r in results)

            return {
                "success": success,
                "flow_id": flow_id,
                "flow_name": flow.name,
                "duration": duration,
                "steps_executed": len(results),
                "results": results,
                "dry_run": dry_run,
            }

        finally:
            if flow_id in self.state.running_flows:
                self.state.running_flows.remove(flow_id)
            self._save_state()

    async def _execute_step(self, step: FlowStep, variables: Dict) -> str:
        """Execute a single step"""
        handler = self.action_handlers.get(step.action_type)
        if handler:
            return await handler(step, variables)
        raise ValueError(f"No handler for action type: {step.action_type}")

    def _render_command(self, step: FlowStep, variables: Dict) -> str:
        """Render a command template with variables"""
        cmd = step.template or step.command
        for key, value in variables.items():
            cmd = cmd.replace(f"${{{key}}}", str(value))
            cmd = cmd.replace(f"${key}", str(value))
        return cmd

    def _check_conditions(self, conditions: List[Dict], variables: Dict) -> bool:
        """Check if conditions are met"""
        for cond in conditions:
            cond_type = cond.get("type", "equals")
            var_name = cond.get("variable", "")
            expected = cond.get("value", "")
            actual = variables.get(var_name, "")

            if cond_type == "equals" and actual != expected:
                return False
            elif cond_type == "not_equals" and actual == expected:
                return False
            elif cond_type == "contains" and expected not in str(actual):
                return False
            elif cond_type == "exists" and not actual:
                return False
            elif cond_type == "file_exists" and not os.path.exists(str(actual)):
                return False

        return True

    # ============================================
    # Action Handlers
    # ============================================

    async def _execute_command(self, step: FlowStep, variables: Dict) -> str:
        """Execute a shell command"""
        cmd = self._render_command(step, variables)

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=variables.get("working_dir"),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=step.timeout
            )

            if proc.returncode != 0 and step.on_error == "stop":
                raise RuntimeError(f"Command failed: {stderr.decode()}")

            return stdout.decode()

        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Command timed out after {step.timeout}s")

    async def _execute_keyboard(self, step: FlowStep, variables: Dict) -> str:
        """Execute keyboard input"""
        keys = step.keystrokes

        await asyncio.create_subprocess_exec(
            "xdotool", "key", "--", keys,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        return f"Sent keys: {keys}"

    async def _execute_click(self, step: FlowStep, variables: Dict) -> str:
        """Execute mouse click"""
        if step.coordinates:
            x, y = step.coordinates
            await asyncio.create_subprocess_exec(
                "xdotool", "mousemove", str(x), str(y), "click", "1",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return f"Clicked at ({x}, {y})"
        return "No coordinates specified"

    async def _execute_app_launch(self, step: FlowStep, variables: Dict) -> str:
        """Launch an application"""
        app = self._render_command(step, variables)

        await asyncio.create_subprocess_shell(
            f"{app} &",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        return f"Launched: {app}"

    async def _execute_file_open(self, step: FlowStep, variables: Dict) -> str:
        """Open a file"""
        path = self._render_command(step, variables)

        await asyncio.create_subprocess_exec(
            "xdg-open", path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        return f"Opened: {path}"

    async def _execute_clipboard(self, step: FlowStep, variables: Dict) -> str:
        """Execute clipboard action"""
        content = self._render_command(step, variables)

        proc = await asyncio.create_subprocess_exec(
            "xclip", "-selection", "clipboard",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate(content.encode())

        return f"Copied to clipboard: {content[:50]}..."


# ============================================
# AI Analysis Agents
# ============================================

class FlowAnalyzer:
    """AI-powered analysis of recordings to generate flows"""

    def __init__(self, ollama_model: str = "purma",
                 remote_provider: str = None,
                 remote_api_key: str = None):
        self.ollama_model = ollama_model
        self.remote_provider = remote_provider
        self.remote_api_key = remote_api_key

    async def analyze_recording(self, recording: Recording,
                                 use_remote: bool = False) -> Dict:
        """Analyze a recording and extract workflow patterns"""

        actions_text = self._format_actions_for_ai(recording.actions)

        prompt = f"""Analyze this sequence of user actions and identify:
1. The main intent/goal of the user
2. Any repeatable patterns
3. Variables that might change between runs (like filenames, paths)
4. Suggested triggers to automate this workflow
5. Potential optimizations or shortcuts

User Actions:
{actions_text}

Context:
- Started in window: {recording.initial_window}
- Working directory: {recording.initial_directory}

Respond in JSON format:
{{
    "intent": "Main goal of this workflow",
    "summary": "Brief description of what happens",
    "patterns": [
        {{"pattern": "description", "frequency": 1, "importance": "high/medium/low"}}
    ],
    "variables": [
        {{"name": "var_name", "type": "string/path/number", "example": "value", "prompt": "Question to ask user"}}
    ],
    "suggested_triggers": [
        {{"type": "trigger_type", "config": {{}}, "reason": "why this trigger"}}
    ],
    "optimizations": ["suggestion 1", "suggestion 2"],
    "steps": [
        {{"action_type": "command/keyboard/etc", "description": "what it does", "command": "actual command", "is_variable": false}}
    ]
}}"""

        if use_remote and self.remote_provider:
            result = await self._call_remote_ai(prompt)
        else:
            result = await self._call_ollama(prompt)

        return result

    async def suggest_improvements(self, flow: Flow) -> List[str]:
        """Get AI suggestions to improve a flow"""

        steps_text = "\n".join([
            f"- {s.description}: {s.command or s.keystrokes}"
            for s in flow.steps
        ])

        prompt = f"""Review this automation workflow and suggest improvements:

Workflow: {flow.name}
Description: {flow.description}

Steps:
{steps_text}

Triggers: {[t.type for t in flow.triggers]}

Suggest:
1. Performance optimizations
2. Error handling improvements
3. Additional triggers that would be useful
4. Steps that could be combined or parallelized
5. Safety checks that should be added

Respond as a JSON array of suggestions:
["suggestion 1", "suggestion 2", ...]"""

        if self.remote_provider:
            result = await self._call_remote_ai(prompt)
        else:
            result = await self._call_ollama(prompt)

        return result if isinstance(result, list) else []

    async def generate_flow_from_description(self, description: str) -> Dict:
        """Generate a flow from natural language description"""

        prompt = f"""Create an automation workflow based on this description:

"{description}"

Generate a complete workflow with:
1. A descriptive name
2. Step-by-step actions
3. Variables for customizable parts
4. Suggested triggers

Respond in JSON format:
{{
    "name": "Workflow name",
    "description": "What it does",
    "icon": "emoji",
    "variables": {{"var_name": "default_value"}},
    "variable_prompts": {{"var_name": "Question to ask"}},
    "steps": [
        {{"action_type": "command", "description": "Step description", "command": "command with ${{variables}}", "timeout": 30}}
    ],
    "triggers": [
        {{"type": "manual"}}
    ],
    "tags": ["tag1", "tag2"]
}}"""

        if self.remote_provider:
            result = await self._call_remote_ai(prompt)
        else:
            result = await self._call_ollama(prompt)

        return result

    def _format_actions_for_ai(self, actions: List[RecordedAction]) -> str:
        """Format recorded actions for AI analysis"""
        lines = []
        for i, action in enumerate(actions, 1):
            if action.type == ActionType.COMMAND:
                lines.append(f"{i}. [COMMAND] $ {action.data.get('command', '')}")
                if action.data.get('output'):
                    lines.append(f"   Output: {action.data['output'][:200]}")
            elif action.type == ActionType.CLIPBOARD:
                lines.append(f"{i}. [CLIPBOARD] {action.data.get('action', 'copy')}: {action.data.get('content', '')[:100]}")
            elif action.type == ActionType.FILE_OPEN:
                lines.append(f"{i}. [FILE] Opened: {action.data.get('path', '')}")
            elif action.type == ActionType.APP_LAUNCH:
                lines.append(f"{i}. [APP] Launched: {action.data.get('app', '')}")
            elif action.type == ActionType.KEYBOARD:
                lines.append(f"{i}. [KEYS] Pressed: {action.data.get('keys', '')}")
            else:
                lines.append(f"{i}. [{action.type.upper()}] {action.data}")

        return "\n".join(lines)

    async def _call_ollama(self, prompt: str) -> Any:
        """Call local Ollama model"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return json.loads(result.get("response", "{}"))
                else:
                    return {"error": f"Ollama error: {response.status_code}"}

        except Exception as e:
            return {"error": f"Ollama connection failed: {str(e)}"}

    async def _call_remote_ai(self, prompt: str) -> Any:
        """Call remote AI provider (Anthropic/OpenAI)"""
        import httpx

        if self.remote_provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.remote_api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }
        elif self.remote_provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.remote_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }
        else:
            return {"error": "Unknown remote provider"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=data)

                if response.status_code == 200:
                    result = response.json()
                    if self.remote_provider == "anthropic":
                        text = result["content"][0]["text"]
                    else:
                        text = result["choices"][0]["message"]["content"]
                    return json.loads(text)
                else:
                    return {"error": f"API error: {response.status_code}"}

        except Exception as e:
            return {"error": f"Remote AI failed: {str(e)}"}


# ============================================
# Trigger Watcher
# ============================================

class TriggerWatcher:
    """Watches for trigger conditions and executes flows"""

    def __init__(self, flow_manager: FlowManager):
        self.flow_manager = flow_manager
        self.running = False
        self.watchers: Dict[str, asyncio.Task] = {}

    async def start(self):
        """Start watching all enabled triggers"""
        self.running = True

        for flow in self.flow_manager.flows.values():
            if not flow.enabled:
                continue

            for trigger in flow.triggers:
                if not trigger.enabled:
                    continue

                watcher = await self._create_watcher(flow.id, trigger)
                if watcher:
                    self.watchers[f"{flow.id}:{trigger.id}"] = watcher

    async def stop(self):
        """Stop all watchers"""
        self.running = False
        for task in self.watchers.values():
            task.cancel()
        self.watchers.clear()

    async def _create_watcher(self, flow_id: str, trigger: FlowTrigger) -> Optional[asyncio.Task]:
        """Create a watcher for a specific trigger"""

        if trigger.type == TriggerType.DIRECTORY_WATCH:
            return asyncio.create_task(
                self._watch_directory(flow_id, trigger.config)
            )
        elif trigger.type == TriggerType.TIME_SCHEDULE:
            return asyncio.create_task(
                self._watch_schedule(flow_id, trigger.config)
            )

        return None

    async def _watch_directory(self, flow_id: str, config: Dict):
        """Watch a directory for changes"""
        path = os.path.expanduser(config.get("path", "~/"))
        events = config.get("events", ["create"])
        pattern = config.get("pattern", "*")

        # Use inotifywait for directory watching
        while self.running:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "inotifywait", "-q", "-e", ",".join(events), path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )

                stdout, _ = await proc.communicate()
                if stdout and self.running:
                    event_info = stdout.decode().strip()
                    await self.flow_manager.run_flow(
                        flow_id,
                        variables={"trigger_event": event_info}
                    )
            except Exception:
                await asyncio.sleep(5)

    async def _watch_schedule(self, flow_id: str, config: Dict):
        """Watch for scheduled times"""
        interval = config.get("interval", 3600)

        while self.running:
            await asyncio.sleep(interval)
            if self.running:
                await self.flow_manager.run_flow(flow_id)


# ============================================
# Global Instances
# ============================================

flow_manager = FlowManager()
flow_analyzer = FlowAnalyzer()
trigger_watcher = TriggerWatcher(flow_manager)


# ============================================
# Convenience Functions
# ============================================

async def create_flow_from_recording(recording_id: str, use_remote: bool = False) -> Optional[Flow]:
    """Analyze a recording and create a flow from it"""
    recording = flow_manager.recordings.get(recording_id)
    if not recording:
        return None

    analysis = await flow_analyzer.analyze_recording(recording, use_remote)

    if "error" in analysis:
        return None

    steps = []
    for step_data in analysis.get("steps", []):
        step = FlowStep(
            action_type=ActionType(step_data.get("action_type", "command")),
            description=step_data.get("description", ""),
            command=step_data.get("command", ""),
            template=step_data.get("command", ""),
        )
        steps.append(step)

    triggers = [FlowTrigger(type=TriggerType.MANUAL)]
    for trig_data in analysis.get("suggested_triggers", []):
        try:
            triggers.append(FlowTrigger(
                type=TriggerType(trig_data.get("type", "manual")),
                config=trig_data.get("config", {}),
            ))
        except ValueError:
            pass

    flow = Flow(
        name=analysis.get("summary", recording.name)[:50],
        description=analysis.get("intent", ""),
        steps=steps,
        triggers=triggers,
        variables={v["name"]: v.get("example", "") for v in analysis.get("variables", [])},
        variable_prompts={v["name"]: v.get("prompt", "") for v in analysis.get("variables", [])},
        ai_summary=analysis.get("intent", ""),
        ai_suggestions=analysis.get("optimizations", []),
        original_recording_id=recording_id,
    )

    flow_manager.flows[flow.id] = flow
    flow_manager._save_flow(flow)

    recording.analyzed = True
    recording.detected_intent = analysis.get("intent", "")
    recording.generated_flow_id = flow.id
    flow_manager._save_recording(recording)

    return flow
