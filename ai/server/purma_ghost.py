"""
PurmaLinux - Ghost Engine
Shadow AI that observes user behavior and suggests automations

Features:
- Silently observes repetitive actions
- Detects patterns without being asked
- Suggests automations proactively
- Learns from user acceptance/rejection
- Non-intrusive notifications
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import threading
import time
import subprocess
import re
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Action:
    """Represents a user action"""
    action_type: str  # "command", "file_op", "app_switch", "clipboard", "typing"
    target: str       # Command, file path, app name, etc.
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict = field(default_factory=dict)  # Current app, workspace, etc.

@dataclass
class ActionSequence:
    """A sequence of actions that might be automatable"""
    id: str
    actions: List[Action]
    frequency: int = 1
    last_seen: datetime = None
    first_seen: datetime = None
    time_saved_seconds: int = 0
    automation_suggested: bool = False
    user_response: str = None  # "accepted", "rejected", "ignored"

@dataclass
class Suggestion:
    """An automation suggestion"""
    id: str
    title: str
    description: str
    trigger: str
    actions: List[Dict]
    confidence: float
    potential_time_saved: str
    sequence_id: str = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Observation:
    """A single observation/insight"""
    observation_type: str  # "repetition", "inefficiency", "pattern", "opportunity"
    description: str
    evidence: List[Dict]
    suggestion: Optional[Suggestion] = None
    priority: int = 1  # 1-5, 5 being highest


# ═══════════════════════════════════════════════════════════════════════════════
#  Ghost Storage
# ═══════════════════════════════════════════════════════════════════════════════

class GhostStorage:
    """SQLite storage for Ghost observations"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            data_dir = os.path.expanduser("~/.local/share/purma/ghost")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "ghost.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Actions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target TEXT,
                details TEXT,
                context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Detected sequences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequences (
                id TEXT PRIMARY KEY,
                actions TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                first_seen DATETIME,
                last_seen DATETIME,
                time_saved_seconds INTEGER DEFAULT 0,
                automation_suggested INTEGER DEFAULT 0,
                user_response TEXT
            )
        """)

        # Suggestions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                trigger TEXT,
                actions TEXT,
                confidence REAL,
                potential_time_saved TEXT,
                sequence_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                responded_at DATETIME
            )
        """)

        # Observations history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_type TEXT,
                description TEXT,
                evidence TEXT,
                priority INTEGER DEFAULT 1,
                shown_to_user INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User preferences (what they don't want suggestions for)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Command frequency tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_frequency (
                command TEXT PRIMARY KEY,
                count INTEGER DEFAULT 1,
                last_used DATETIME,
                avg_time_between_uses REAL
            )
        """)

        conn.commit()
        conn.close()

    def record_action(self, action: Action):
        """Record a user action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO actions (action_type, target, details, context, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            action.action_type,
            action.target,
            json.dumps(action.details),
            json.dumps(action.context),
            action.timestamp.isoformat()
        ))

        conn.commit()
        conn.close()

    def get_recent_actions(self, minutes: int = 30, limit: int = 100) -> List[Dict]:
        """Get recent actions within time window"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        cursor.execute("""
            SELECT action_type, target, details, context, timestamp
            FROM actions
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (since, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "action_type": row[0],
                "target": row[1],
                "details": json.loads(row[2]) if row[2] else {},
                "context": json.loads(row[3]) if row[3] else {},
                "timestamp": row[4]
            })

        conn.close()
        return results

    def save_sequence(self, sequence: ActionSequence):
        """Save a detected sequence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        actions_json = json.dumps([asdict(a) for a in sequence.actions], default=str)

        cursor.execute("""
            INSERT OR REPLACE INTO sequences
            (id, actions, frequency, first_seen, last_seen, time_saved_seconds,
             automation_suggested, user_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sequence.id,
            actions_json,
            sequence.frequency,
            sequence.first_seen.isoformat() if sequence.first_seen else datetime.now().isoformat(),
            sequence.last_seen.isoformat() if sequence.last_seen else datetime.now().isoformat(),
            sequence.time_saved_seconds,
            1 if sequence.automation_suggested else 0,
            sequence.user_response
        ))

        conn.commit()
        conn.close()

    def get_sequences(self, min_frequency: int = 3) -> List[Dict]:
        """Get detected sequences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, actions, frequency, first_seen, last_seen, time_saved_seconds,
                   automation_suggested, user_response
            FROM sequences
            WHERE frequency >= ?
            ORDER BY frequency DESC
        """, (min_frequency,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "actions": json.loads(row[1]),
                "frequency": row[2],
                "first_seen": row[3],
                "last_seen": row[4],
                "time_saved_seconds": row[5],
                "automation_suggested": bool(row[6]),
                "user_response": row[7]
            })

        conn.close()
        return results

    def save_suggestion(self, suggestion: Suggestion):
        """Save a suggestion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO suggestions
            (id, title, description, trigger, actions, confidence,
             potential_time_saved, sequence_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            suggestion.id,
            suggestion.title,
            suggestion.description,
            suggestion.trigger,
            json.dumps(suggestion.actions),
            suggestion.confidence,
            suggestion.potential_time_saved,
            suggestion.sequence_id,
            suggestion.created_at.isoformat()
        ))

        conn.commit()
        conn.close()

    def get_pending_suggestions(self, limit: int = 10) -> List[Dict]:
        """Get pending suggestions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, description, trigger, actions, confidence,
                   potential_time_saved, sequence_id, created_at
            FROM suggestions
            WHERE status = 'pending'
            ORDER BY confidence DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "trigger": row[3],
                "actions": json.loads(row[4]) if row[4] else [],
                "confidence": row[5],
                "potential_time_saved": row[6],
                "sequence_id": row[7],
                "created_at": row[8]
            })

        conn.close()
        return results

    def respond_to_suggestion(self, suggestion_id: str, response: str):
        """Record user response to suggestion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE suggestions
            SET status = ?, responded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (response, suggestion_id))

        conn.commit()
        conn.close()

    def update_command_frequency(self, command: str):
        """Update command usage frequency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO command_frequency (command, count, last_used)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(command) DO UPDATE SET
                count = count + 1,
                last_used = CURRENT_TIMESTAMP
        """, (command,))

        conn.commit()
        conn.close()

    def get_frequent_commands(self, min_count: int = 5, limit: int = 20) -> List[Dict]:
        """Get frequently used commands"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT command, count, last_used
            FROM command_frequency
            WHERE count >= ?
            ORDER BY count DESC
            LIMIT ?
        """, (min_count, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "command": row[0],
                "count": row[1],
                "last_used": row[2]
            })

        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get Ghost statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM actions")
        total_actions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sequences")
        total_sequences = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM suggestions WHERE status = 'pending'")
        pending_suggestions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM suggestions WHERE status = 'accepted'")
        accepted_suggestions = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(time_saved_seconds) FROM sequences WHERE user_response = 'accepted'")
        time_saved = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_actions_observed": total_actions,
            "patterns_detected": total_sequences,
            "pending_suggestions": pending_suggestions,
            "accepted_suggestions": accepted_suggestions,
            "total_time_saved_seconds": time_saved,
            "total_time_saved_minutes": round(time_saved / 60, 1)
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Action Observer
# ═══════════════════════════════════════════════════════════════════════════════

class ActionObserver:
    """Observes user actions from various sources"""

    def __init__(self, storage: GhostStorage):
        self.storage = storage
        self.observing = False
        self._threads = []
        self.current_context = {}

    def _get_context(self) -> Dict:
        """Get current context (active app, workspace, etc.)"""
        context = {
            "timestamp": datetime.now().isoformat()
        }

        # Get active window
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowclassname"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                context["active_app"] = result.stdout.strip()
        except:
            pass

        # Get workspace
        try:
            result = subprocess.run(
                ["wmctrl", "-d"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "*" in line:
                        context["workspace"] = int(line.split()[0]) + 1
                        break
        except:
            pass

        self.current_context = context
        return context

    def _observe_shell_history(self):
        """Monitor shell command history"""
        history_files = [
            os.path.expanduser("~/.bash_history"),
            os.path.expanduser("~/.zsh_history"),
            os.path.expanduser("~/.local/share/fish/fish_history")
        ]

        last_positions = {}

        while self.observing:
            for history_file in history_files:
                if not os.path.exists(history_file):
                    continue

                try:
                    with open(history_file, "r", errors="ignore") as f:
                        f.seek(last_positions.get(history_file, 0))
                        new_lines = f.readlines()
                        last_positions[history_file] = f.tell()

                        for line in new_lines:
                            # Parse command (handle zsh extended history format)
                            command = line.strip()
                            if command.startswith(":"):
                                # Zsh format: : timestamp:0;command
                                parts = command.split(";", 1)
                                if len(parts) > 1:
                                    command = parts[1]
                                else:
                                    continue

                            if command and not command.startswith("#"):
                                action = Action(
                                    action_type="command",
                                    target=command,
                                    context=self._get_context()
                                )
                                self.storage.record_action(action)
                                self.storage.update_command_frequency(command.split()[0])

                except Exception as e:
                    pass

            time.sleep(2)

    def _observe_clipboard(self):
        """Monitor clipboard changes"""
        last_clipboard = ""

        while self.observing:
            try:
                result = subprocess.run(
                    ["wl-paste", "-n"],
                    capture_output=True, text=True, timeout=2
                )

                if result.returncode == 0:
                    current = result.stdout

                    if current != last_clipboard and len(current) < 10000:
                        # Record clipboard action
                        action = Action(
                            action_type="clipboard",
                            target="copy",
                            details={"length": len(current), "preview": current[:100]},
                            context=self._get_context()
                        )
                        self.storage.record_action(action)
                        last_clipboard = current

            except:
                pass

            time.sleep(1)

    def _observe_file_events(self):
        """Monitor file system events (requires inotify)"""
        watched_dirs = [
            os.path.expanduser("~"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop")
        ]

        try:
            import inotify.adapters
            notifier = inotify.adapters.Inotify()

            for d in watched_dirs:
                if os.path.exists(d):
                    notifier.add_watch(d)

            for event in notifier.event_gen(yield_nones=False):
                if not self.observing:
                    break

                (_, type_names, path, filename) = event

                if filename.startswith("."):
                    continue

                for event_type in type_names:
                    if event_type in ("IN_CREATE", "IN_MODIFY", "IN_DELETE", "IN_MOVED_TO"):
                        action = Action(
                            action_type="file_op",
                            target=os.path.join(path, filename),
                            details={"operation": event_type},
                            context=self._get_context()
                        )
                        self.storage.record_action(action)

        except ImportError:
            # inotify not available, skip file monitoring
            pass

    def start(self):
        """Start observing"""
        if not self.observing:
            self.observing = True

            # Start observer threads
            threads = [
                threading.Thread(target=self._observe_shell_history, daemon=True),
                threading.Thread(target=self._observe_clipboard, daemon=True),
                threading.Thread(target=self._observe_file_events, daemon=True),
            ]

            for t in threads:
                t.start()
                self._threads.append(t)

    def stop(self):
        """Stop observing"""
        self.observing = False
        for t in self._threads:
            t.join(timeout=2)
        self._threads = []


# ═══════════════════════════════════════════════════════════════════════════════
#  Pattern Detector
# ═══════════════════════════════════════════════════════════════════════════════

class PatternDetector:
    """Detects patterns and repetitive behaviors"""

    def __init__(self, storage: GhostStorage):
        self.storage = storage

    def _hash_sequence(self, actions: List[Dict]) -> str:
        """Create a hash for a sequence of actions"""
        normalized = []
        for a in actions:
            normalized.append(f"{a['action_type']}:{a['target']}")
        return hashlib.sha256("|".join(normalized).encode()).hexdigest()[:16]

    def detect_command_sequences(self, window_minutes: int = 60) -> List[Dict]:
        """Detect repeated command sequences"""
        actions = self.storage.get_recent_actions(minutes=window_minutes, limit=500)

        # Filter to commands only
        commands = [a for a in actions if a["action_type"] == "command"]

        if len(commands) < 3:
            return []

        # Find repeated sequences of 2-5 commands
        sequences_found = defaultdict(list)

        for seq_len in range(2, 6):
            for i in range(len(commands) - seq_len + 1):
                seq = commands[i:i + seq_len]
                seq_hash = self._hash_sequence(seq)
                sequences_found[seq_hash].append({
                    "actions": seq,
                    "timestamp": seq[0]["timestamp"]
                })

        # Filter to sequences that occur multiple times
        repeated = []
        for seq_hash, occurrences in sequences_found.items():
            if len(occurrences) >= 2:
                repeated.append({
                    "id": seq_hash,
                    "actions": occurrences[0]["actions"],
                    "frequency": len(occurrences),
                    "timestamps": [o["timestamp"] for o in occurrences]
                })

        return sorted(repeated, key=lambda x: x["frequency"], reverse=True)

    def detect_time_patterns(self) -> List[Dict]:
        """Detect time-based patterns (things done at same time daily)"""
        actions = self.storage.get_recent_actions(minutes=24*60*7, limit=1000)  # Last week

        # Group by hour and action
        hour_actions = defaultdict(lambda: defaultdict(int))

        for action in actions:
            try:
                ts = datetime.fromisoformat(action["timestamp"])
                hour = ts.hour
                action_key = f"{action['action_type']}:{action['target']}"
                hour_actions[hour][action_key] += 1
            except:
                pass

        patterns = []
        for hour, actions_count in hour_actions.items():
            for action_key, count in actions_count.items():
                if count >= 3:  # At least 3 times at this hour
                    patterns.append({
                        "hour": hour,
                        "action": action_key,
                        "frequency": count,
                        "type": "time_based"
                    })

        return patterns

    def detect_inefficiencies(self) -> List[Dict]:
        """Detect potentially inefficient behaviors"""
        inefficiencies = []

        # Check for repeated long commands that could be aliased
        frequent_commands = self.storage.get_frequent_commands(min_count=5)

        for cmd in frequent_commands:
            command = cmd["command"]
            if len(command) > 30 and cmd["count"] >= 5:
                inefficiencies.append({
                    "type": "long_repeated_command",
                    "command": command,
                    "count": cmd["count"],
                    "suggestion": f"Create an alias for this command",
                    "potential_time_saved": f"{cmd['count'] * 3} seconds"
                })

        # Check for cd + command patterns (could use full paths or aliases)
        actions = self.storage.get_recent_actions(minutes=60*24, limit=500)
        commands = [a for a in actions if a["action_type"] == "command"]

        cd_followed_by = defaultdict(int)
        for i in range(len(commands) - 1):
            if commands[i]["target"].startswith("cd "):
                next_cmd = commands[i + 1]["target"].split()[0]
                cd_followed_by[next_cmd] += 1

        for cmd, count in cd_followed_by.items():
            if count >= 5:
                inefficiencies.append({
                    "type": "cd_then_command",
                    "command": cmd,
                    "count": count,
                    "suggestion": f"Create a function or alias that combines cd and {cmd}",
                    "potential_time_saved": f"{count * 2} seconds"
                })

        return inefficiencies


# ═══════════════════════════════════════════════════════════════════════════════
#  Suggestion Generator
# ═══════════════════════════════════════════════════════════════════════════════

class SuggestionGenerator:
    """Generates automation suggestions from patterns"""

    def __init__(self, storage: GhostStorage):
        self.storage = storage

    def generate_from_sequence(self, sequence: Dict) -> Optional[Suggestion]:
        """Generate suggestion from a command sequence"""
        actions = sequence["actions"]

        if len(actions) < 2:
            return None

        # Extract commands
        commands = [a["target"] for a in actions]
        frequency = sequence["frequency"]

        # Estimate time saved
        total_chars = sum(len(c) for c in commands)
        time_per_use = total_chars * 0.1  # ~0.1 seconds per character
        total_time_saved = time_per_use * frequency

        # Generate suggestion
        suggestion_id = hashlib.sha256(json.dumps(commands).encode()).hexdigest()[:12]

        title = f"Automate: {commands[0].split()[0]} → {commands[-1].split()[0]}"

        # Create shell function
        func_name = f"purma_auto_{suggestion_id[:6]}"
        shell_function = f"""
# Auto-generated by Purma Ghost
{func_name}() {{
    {chr(10).join('    ' + c for c in commands)}
}}
"""

        return Suggestion(
            id=suggestion_id,
            title=title,
            description=f"You run these {len(commands)} commands together {frequency} times. "
                        f"Consider creating a function or alias.",
            trigger=commands[0],
            actions=[{"type": "shell_function", "code": shell_function}],
            confidence=min(0.5 + (frequency * 0.1), 0.95),
            potential_time_saved=f"{int(total_time_saved)} seconds",
            sequence_id=sequence["id"]
        )

    def generate_alias_suggestion(self, command: str, count: int) -> Suggestion:
        """Generate alias suggestion for long command"""
        # Extract base command name
        base_cmd = command.split()[0]
        alias_name = f"p{base_cmd[:3]}"  # Short alias

        suggestion_id = hashlib.sha256(command.encode()).hexdigest()[:12]

        return Suggestion(
            id=suggestion_id,
            title=f"Create alias for: {base_cmd}",
            description=f"You've typed this {count} times. Create a shorter alias.",
            trigger=command,
            actions=[{
                "type": "alias",
                "code": f"alias {alias_name}='{command}'"
            }],
            confidence=min(0.4 + (count * 0.05), 0.9),
            potential_time_saved=f"{count * 2} seconds"
        )

    def generate_all_suggestions(self, detector: PatternDetector) -> List[Suggestion]:
        """Generate all pending suggestions"""
        suggestions = []

        # From command sequences
        sequences = detector.detect_command_sequences()
        for seq in sequences[:5]:  # Top 5 sequences
            suggestion = self.generate_from_sequence(seq)
            if suggestion:
                suggestions.append(suggestion)

        # From long commands
        frequent_commands = self.storage.get_frequent_commands(min_count=5)
        for cmd_info in frequent_commands:
            if len(cmd_info["command"]) > 30:
                suggestion = self.generate_alias_suggestion(
                    cmd_info["command"],
                    cmd_info["count"]
                )
                suggestions.append(suggestion)

        # Save and return
        for suggestion in suggestions:
            self.storage.save_suggestion(suggestion)

        return suggestions


# ═══════════════════════════════════════════════════════════════════════════════
#  Ghost Engine
# ═══════════════════════════════════════════════════════════════════════════════

class GhostEngine:
    """Main Ghost engine - coordinates observation and suggestions"""

    def __init__(self):
        self.storage = GhostStorage()
        self.observer = ActionObserver(self.storage)
        self.detector = PatternDetector(self.storage)
        self.suggester = SuggestionGenerator(self.storage)
        self.enabled = False

    def start(self):
        """Start Ghost observation"""
        self.enabled = True
        self.observer.start()
        return {"status": "ghost_started", "message": "Ghost is now observing..."}

    def stop(self):
        """Stop Ghost observation"""
        self.enabled = False
        self.observer.stop()
        return {"status": "ghost_stopped"}

    def get_status(self) -> Dict:
        """Get Ghost status"""
        stats = self.storage.get_stats()
        pending = self.storage.get_pending_suggestions(limit=5)

        return {
            "enabled": self.enabled,
            "observing": self.observer.observing,
            "stats": stats,
            "pending_suggestions": len(pending),
            "recent_patterns": len(self.detector.detect_command_sequences())
        }

    def analyze(self) -> Dict:
        """Run analysis and generate suggestions"""
        # Detect patterns
        sequences = self.detector.detect_command_sequences()
        time_patterns = self.detector.detect_time_patterns()
        inefficiencies = self.detector.detect_inefficiencies()

        # Generate suggestions
        suggestions = self.suggester.generate_all_suggestions(self.detector)

        return {
            "sequences_detected": len(sequences),
            "time_patterns": len(time_patterns),
            "inefficiencies": len(inefficiencies),
            "suggestions_generated": len(suggestions),
            "top_sequences": sequences[:3],
            "top_inefficiencies": inefficiencies[:3]
        }

    def get_suggestions(self, limit: int = 10) -> List[Dict]:
        """Get pending suggestions"""
        return self.storage.get_pending_suggestions(limit=limit)

    def respond_to_suggestion(self, suggestion_id: str, response: str) -> Dict:
        """Accept, reject, or dismiss a suggestion"""
        if response not in ("accepted", "rejected", "dismissed"):
            return {"error": "Invalid response. Use: accepted, rejected, dismissed"}

        self.storage.respond_to_suggestion(suggestion_id, response)

        if response == "accepted":
            # TODO: Actually implement the automation
            return {"status": "accepted", "message": "Automation will be added"}
        elif response == "rejected":
            return {"status": "rejected", "message": "Suggestion rejected, won't show again"}
        else:
            return {"status": "dismissed", "message": "Suggestion dismissed"}

    def get_insights(self) -> List[Dict]:
        """Get observational insights"""
        insights = []

        stats = self.storage.get_stats()

        # Insight about observation depth
        insights.append({
            "type": "observation_summary",
            "title": "Observation Summary",
            "description": f"Ghost has observed {stats['total_actions_observed']} actions "
                          f"and detected {stats['patterns_detected']} patterns."
        })

        # Most frequent commands
        frequent = self.storage.get_frequent_commands(min_count=10, limit=5)
        if frequent:
            insights.append({
                "type": "frequent_commands",
                "title": "Your Most Used Commands",
                "data": frequent
            })

        # Time savings potential
        if stats['pending_suggestions'] > 0:
            insights.append({
                "type": "potential_savings",
                "title": "Potential Time Savings",
                "description": f"You have {stats['pending_suggestions']} automation opportunities "
                              f"that could save you time."
            })

        # Already automated
        if stats['total_time_saved_seconds'] > 0:
            insights.append({
                "type": "time_saved",
                "title": "Time Already Saved",
                "description": f"Ghost automations have saved you "
                              f"{stats['total_time_saved_minutes']} minutes."
            })

        return insights

    def apply_suggestion(self, suggestion_id: str) -> Dict:
        """Apply an accepted suggestion"""
        suggestions = self.storage.get_pending_suggestions(limit=100)
        suggestion = next((s for s in suggestions if s["id"] == suggestion_id), None)

        if not suggestion:
            return {"error": "Suggestion not found"}

        # Apply based on type
        for action in suggestion.get("actions", []):
            action_type = action.get("type")
            code = action.get("code", "")

            if action_type == "alias":
                # Add to shell rc file
                rc_files = [
                    os.path.expanduser("~/.bashrc"),
                    os.path.expanduser("~/.zshrc")
                ]

                for rc_file in rc_files:
                    if os.path.exists(rc_file):
                        with open(rc_file, "a") as f:
                            f.write(f"\n# Added by Purma Ghost\n{code}\n")

                return {"status": "applied", "type": "alias", "added_to": rc_files}

            elif action_type == "shell_function":
                # Add function to shell rc
                rc_file = os.path.expanduser("~/.bashrc")
                if os.path.exists(os.path.expanduser("~/.zshrc")):
                    rc_file = os.path.expanduser("~/.zshrc")

                with open(rc_file, "a") as f:
                    f.write(f"\n{code}\n")

                return {"status": "applied", "type": "function", "added_to": rc_file}

        return {"status": "no_action", "message": "No applicable action found"}


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════

_ghost_engine = None

def get_ghost_engine() -> GhostEngine:
    global _ghost_engine
    if _ghost_engine is None:
        _ghost_engine = GhostEngine()
    return _ghost_engine
