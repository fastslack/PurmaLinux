"""
PurmaLinux - Cortex Engine
Predictive AI that learns user patterns and anticipates needs

Features:
- Tracks app usage patterns (what apps, when, what context)
- Learns workflow sequences (app A -> app B -> app C)
- Predicts next actions based on time, day, context
- Prepares workspaces proactively
- Suggests optimizations based on habits
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import subprocess
import threading
import time
import math

# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AppEvent:
    """Represents an application usage event"""
    app_name: str
    window_title: str
    timestamp: datetime
    duration_seconds: int = 0
    workspace: int = 1
    day_of_week: int = 0  # 0=Monday, 6=Sunday
    hour_of_day: int = 0
    context_tags: List[str] = None

    def __post_init__(self):
        if self.context_tags is None:
            self.context_tags = []
        self.day_of_week = self.timestamp.weekday()
        self.hour_of_day = self.timestamp.hour

@dataclass
class Pattern:
    """A learned behavioral pattern"""
    pattern_type: str  # "sequence", "time", "context", "cooccurrence"
    apps: List[str]
    confidence: float
    occurrences: int
    time_range: Tuple[int, int] = None  # (start_hour, end_hour)
    days: List[int] = None  # Days of week
    context: str = None

@dataclass
class Prediction:
    """A prediction for user's next action"""
    action_type: str  # "open_app", "switch_workspace", "prepare_env"
    target: str
    confidence: float
    reason: str
    suggested_time: datetime = None

# ═══════════════════════════════════════════════════════════════════════════════
#  Pattern Storage
# ═══════════════════════════════════════════════════════════════════════════════

class CortexStorage:
    """SQLite storage for Cortex learning data"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            data_dir = os.path.expanduser("~/.local/share/purma/cortex")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "cortex.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # App events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                timestamp DATETIME NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                workspace INTEGER DEFAULT 1,
                day_of_week INTEGER,
                hour_of_day INTEGER,
                context_tags TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Learned patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                apps TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                occurrences INTEGER DEFAULT 1,
                time_range TEXT,
                days TEXT,
                context TEXT,
                last_seen DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sequences table (app A -> app B)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_app TEXT NOT NULL,
                to_app TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                avg_delay_seconds REAL DEFAULT 0,
                last_seen DATETIME,
                UNIQUE(from_app, to_app)
            )
        """)

        # Time patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                hour INTEGER NOT NULL,
                day_of_week INTEGER,
                count INTEGER DEFAULT 1,
                UNIQUE(app_name, hour, day_of_week)
            )
        """)

        # Co-occurrence table (apps used together)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cooccurrence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app1 TEXT NOT NULL,
                app2 TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                within_minutes INTEGER DEFAULT 5,
                UNIQUE(app1, app2)
            )
        """)

        # Predictions log (for learning from accuracy)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_type TEXT,
                target TEXT,
                confidence REAL,
                was_correct INTEGER DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON app_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_app ON app_events(app_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sequences_from ON sequences(from_app)")

        conn.commit()
        conn.close()

    def record_event(self, event: AppEvent):
        """Record an app usage event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO app_events
            (app_name, window_title, timestamp, duration_seconds, workspace,
             day_of_week, hour_of_day, context_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.app_name,
            event.window_title,
            event.timestamp.isoformat(),
            event.duration_seconds,
            event.workspace,
            event.day_of_week,
            event.hour_of_day,
            json.dumps(event.context_tags)
        ))

        conn.commit()
        conn.close()

    def update_sequence(self, from_app: str, to_app: str, delay_seconds: float):
        """Update app sequence pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sequences (from_app, to_app, count, avg_delay_seconds, last_seen)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(from_app, to_app) DO UPDATE SET
                count = count + 1,
                avg_delay_seconds = (avg_delay_seconds * count + ?) / (count + 1),
                last_seen = CURRENT_TIMESTAMP
        """, (from_app, to_app, delay_seconds, delay_seconds))

        conn.commit()
        conn.close()

    def update_time_pattern(self, app_name: str, hour: int, day_of_week: int):
        """Update time-based usage pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO time_patterns (app_name, hour, day_of_week, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(app_name, hour, day_of_week) DO UPDATE SET
                count = count + 1
        """, (app_name, hour, day_of_week))

        conn.commit()
        conn.close()

    def update_cooccurrence(self, app1: str, app2: str):
        """Update co-occurrence pattern"""
        # Normalize order for consistency
        if app1 > app2:
            app1, app2 = app2, app1

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO cooccurrence (app1, app2, count)
            VALUES (?, ?, 1)
            ON CONFLICT(app1, app2) DO UPDATE SET
                count = count + 1
        """, (app1, app2))

        conn.commit()
        conn.close()

    def get_sequences(self, from_app: str = None, min_count: int = 2) -> List[Dict]:
        """Get app sequences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if from_app:
            cursor.execute("""
                SELECT from_app, to_app, count, avg_delay_seconds
                FROM sequences
                WHERE from_app = ? AND count >= ?
                ORDER BY count DESC
            """, (from_app, min_count))
        else:
            cursor.execute("""
                SELECT from_app, to_app, count, avg_delay_seconds
                FROM sequences
                WHERE count >= ?
                ORDER BY count DESC
                LIMIT 100
            """, (min_count,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "from_app": row[0],
                "to_app": row[1],
                "count": row[2],
                "avg_delay_seconds": row[3]
            })

        conn.close()
        return results

    def get_time_patterns(self, app_name: str = None, hour: int = None, day: int = None) -> List[Dict]:
        """Get time-based patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT app_name, hour, day_of_week, count FROM time_patterns WHERE 1=1"
        params = []

        if app_name:
            query += " AND app_name = ?"
            params.append(app_name)
        if hour is not None:
            query += " AND hour = ?"
            params.append(hour)
        if day is not None:
            query += " AND day_of_week = ?"
            params.append(day)

        query += " ORDER BY count DESC LIMIT 50"

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "app_name": row[0],
                "hour": row[1],
                "day_of_week": row[2],
                "count": row[3]
            })

        conn.close()
        return results

    def get_cooccurrences(self, app_name: str = None, min_count: int = 2) -> List[Dict]:
        """Get co-occurrence patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if app_name:
            cursor.execute("""
                SELECT app1, app2, count
                FROM cooccurrence
                WHERE (app1 = ? OR app2 = ?) AND count >= ?
                ORDER BY count DESC
            """, (app_name, app_name, min_count))
        else:
            cursor.execute("""
                SELECT app1, app2, count
                FROM cooccurrence
                WHERE count >= ?
                ORDER BY count DESC
                LIMIT 50
            """, (min_count,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "app1": row[0],
                "app2": row[1],
                "count": row[2]
            })

        conn.close()
        return results

    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """Get recent app events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT app_name, window_title, timestamp, duration_seconds, workspace
            FROM app_events
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "app_name": row[0],
                "window_title": row[1],
                "timestamp": row[2],
                "duration_seconds": row[3],
                "workspace": row[4]
            })

        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get Cortex statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM app_events")
        total_events = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sequences")
        total_sequences = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM time_patterns")
        total_time_patterns = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cooccurrence")
        total_cooccurrences = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT app_name) FROM app_events")
        unique_apps = cursor.fetchone()[0]

        conn.close()

        return {
            "total_events": total_events,
            "total_sequences": total_sequences,
            "total_time_patterns": total_time_patterns,
            "total_cooccurrences": total_cooccurrences,
            "unique_apps": unique_apps
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Activity Tracker
# ═══════════════════════════════════════════════════════════════════════════════

class ActivityTracker:
    """Tracks user activity (focused window, apps)"""

    def __init__(self, storage: CortexStorage):
        self.storage = storage
        self.current_app = None
        self.current_window = None
        self.current_start = None
        self.recent_apps = []  # Last N apps for sequence detection
        self.tracking = False
        self._thread = None

    def _get_active_window(self) -> Tuple[str, str]:
        """Get current active window info"""
        try:
            # Try xdotool first (X11)
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            window_title = result.stdout.strip() if result.returncode == 0 else ""

            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowclassname"],
                capture_output=True, text=True, timeout=2
            )
            app_name = result.stdout.strip() if result.returncode == 0 else ""

            if app_name:
                return app_name, window_title
        except:
            pass

        try:
            # Try wmctrl
            result = subprocess.run(
                ["wmctrl", "-a", ":ACTIVE:", "-v"],
                capture_output=True, text=True, timeout=2
            )
        except:
            pass

        try:
            # Try hyprctl (Hyprland)
            result = subprocess.run(
                ["hyprctl", "activewindow", "-j"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("class", ""), data.get("title", "")
        except:
            pass

        return "", ""

    def _get_workspace(self) -> int:
        """Get current workspace number"""
        try:
            result = subprocess.run(
                ["wmctrl", "-d"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "*" in line:
                        return int(line.split()[0]) + 1
        except:
            pass
        return 1

    def _track_loop(self):
        """Main tracking loop"""
        while self.tracking:
            try:
                app_name, window_title = self._get_active_window()

                if app_name and app_name != self.current_app:
                    now = datetime.now()

                    # Record previous app's duration
                    if self.current_app and self.current_start:
                        duration = int((now - self.current_start).total_seconds())
                        if duration > 2:  # Ignore very short focuses
                            event = AppEvent(
                                app_name=self.current_app,
                                window_title=self.current_window or "",
                                timestamp=self.current_start,
                                duration_seconds=duration,
                                workspace=self._get_workspace()
                            )
                            self.storage.record_event(event)
                            self.storage.update_time_pattern(
                                self.current_app,
                                self.current_start.hour,
                                self.current_start.weekday()
                            )

                    # Track sequence
                    if self.current_app and app_name:
                        delay = (now - self.current_start).total_seconds() if self.current_start else 0
                        self.storage.update_sequence(self.current_app, app_name, delay)

                    # Track co-occurrence (apps used within 5 minutes)
                    self.recent_apps.append((app_name, now))
                    self.recent_apps = [(a, t) for a, t in self.recent_apps
                                        if (now - t).total_seconds() < 300]

                    recent_app_names = list(set(a for a, t in self.recent_apps))
                    for i, app1 in enumerate(recent_app_names):
                        for app2 in recent_app_names[i+1:]:
                            self.storage.update_cooccurrence(app1, app2)

                    # Update current
                    self.current_app = app_name
                    self.current_window = window_title
                    self.current_start = now

            except Exception as e:
                print(f"Tracking error: {e}")

            time.sleep(1)  # Check every second

    def start(self):
        """Start tracking"""
        if not self.tracking:
            self.tracking = True
            self._thread = threading.Thread(target=self._track_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop tracking"""
        self.tracking = False
        if self._thread:
            self._thread.join(timeout=2)


# ═══════════════════════════════════════════════════════════════════════════════
#  Prediction Engine
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionEngine:
    """Generates predictions based on learned patterns"""

    def __init__(self, storage: CortexStorage):
        self.storage = storage

    def predict_next_app(self, current_app: str = None, limit: int = 5) -> List[Prediction]:
        """Predict what app the user will open next"""
        predictions = []
        now = datetime.now()

        # 1. Sequence-based predictions
        if current_app:
            sequences = self.storage.get_sequences(from_app=current_app, min_count=2)
            total_count = sum(s["count"] for s in sequences)

            for seq in sequences[:3]:
                confidence = seq["count"] / max(total_count, 1)
                predictions.append(Prediction(
                    action_type="open_app",
                    target=seq["to_app"],
                    confidence=min(confidence * 0.8, 0.9),  # Cap at 90%
                    reason=f"You usually open {seq['to_app']} after {current_app} ({seq['count']} times)"
                ))

        # 2. Time-based predictions
        time_patterns = self.storage.get_time_patterns(
            hour=now.hour,
            day=now.weekday()
        )

        for pattern in time_patterns[:3]:
            # Check if already in predictions
            if any(p.target == pattern["app_name"] for p in predictions):
                # Boost confidence
                for p in predictions:
                    if p.target == pattern["app_name"]:
                        p.confidence = min(p.confidence + 0.1, 0.95)
                        p.reason += f" (also common at this time)"
            else:
                confidence = min(pattern["count"] / 20, 0.7)  # Normalize
                predictions.append(Prediction(
                    action_type="open_app",
                    target=pattern["app_name"],
                    confidence=confidence,
                    reason=f"You often use {pattern['app_name']} at {now.hour}:00 on {self._day_name(now.weekday())}"
                ))

        # Sort by confidence and return top N
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:limit]

    def predict_workflow(self, current_app: str = None) -> List[Prediction]:
        """Predict a likely workflow sequence"""
        predictions = []

        if not current_app:
            return predictions

        # Build workflow chain
        workflow = [current_app]
        visited = {current_app}

        for _ in range(5):  # Max 5 steps
            sequences = self.storage.get_sequences(from_app=workflow[-1], min_count=3)

            # Find most likely next app not already in workflow
            next_app = None
            for seq in sequences:
                if seq["to_app"] not in visited:
                    next_app = seq["to_app"]
                    break

            if next_app:
                workflow.append(next_app)
                visited.add(next_app)
            else:
                break

        if len(workflow) > 1:
            predictions.append(Prediction(
                action_type="prepare_workflow",
                target=json.dumps(workflow),
                confidence=0.7,
                reason=f"Common workflow: {' → '.join(workflow)}"
            ))

        return predictions

    def suggest_companions(self, current_app: str) -> List[Prediction]:
        """Suggest apps commonly used together"""
        predictions = []

        cooccurrences = self.storage.get_cooccurrences(app_name=current_app, min_count=3)

        for co in cooccurrences[:5]:
            companion = co["app1"] if co["app2"] == current_app else co["app2"]
            confidence = min(co["count"] / 10, 0.8)

            predictions.append(Prediction(
                action_type="open_app",
                target=companion,
                confidence=confidence,
                reason=f"You often use {companion} alongside {current_app} ({co['count']} times)"
            ))

        return predictions

    def get_daily_schedule(self) -> List[Dict]:
        """Get predicted daily schedule based on patterns"""
        now = datetime.now()
        schedule = []

        for hour in range(24):
            patterns = self.storage.get_time_patterns(hour=hour, day=now.weekday())
            if patterns:
                top_app = patterns[0]
                schedule.append({
                    "hour": hour,
                    "app": top_app["app_name"],
                    "confidence": min(top_app["count"] / 10, 0.9),
                    "count": top_app["count"]
                })

        return schedule

    def _day_name(self, day: int) -> str:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[day] if 0 <= day < 7 else "Unknown"


# ═══════════════════════════════════════════════════════════════════════════════
#  Cortex Engine
# ═══════════════════════════════════════════════════════════════════════════════

class CortexEngine:
    """Main Cortex engine - coordinates tracking, learning, and predictions"""

    def __init__(self):
        self.storage = CortexStorage()
        self.tracker = ActivityTracker(self.storage)
        self.predictor = PredictionEngine(self.storage)
        self.learning_enabled = True

    def start_learning(self):
        """Start learning from user activity"""
        self.learning_enabled = True
        self.tracker.start()
        return {"status": "learning_started"}

    def stop_learning(self):
        """Stop learning"""
        self.learning_enabled = False
        self.tracker.stop()
        return {"status": "learning_stopped"}

    def get_status(self) -> Dict:
        """Get Cortex status"""
        stats = self.storage.get_stats()
        return {
            "learning_enabled": self.learning_enabled,
            "tracking_active": self.tracker.tracking,
            "current_app": self.tracker.current_app,
            "stats": stats
        }

    def predict(self, current_app: str = None) -> Dict:
        """Get predictions for current context"""
        if current_app is None:
            current_app = self.tracker.current_app

        next_apps = self.predictor.predict_next_app(current_app)
        workflow = self.predictor.predict_workflow(current_app)
        companions = self.predictor.suggest_companions(current_app) if current_app else []

        return {
            "current_app": current_app,
            "predictions": {
                "next_apps": [
                    {
                        "app": p.target,
                        "confidence": round(p.confidence, 2),
                        "reason": p.reason
                    }
                    for p in next_apps
                ],
                "workflow": [
                    {
                        "apps": json.loads(p.target),
                        "confidence": round(p.confidence, 2),
                        "reason": p.reason
                    }
                    for p in workflow
                ],
                "companions": [
                    {
                        "app": p.target,
                        "confidence": round(p.confidence, 2),
                        "reason": p.reason
                    }
                    for p in companions
                ]
            }
        }

    def get_schedule(self) -> Dict:
        """Get predicted daily schedule"""
        schedule = self.predictor.get_daily_schedule()
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "day": datetime.now().strftime("%A"),
            "schedule": schedule
        }

    def get_patterns(self) -> Dict:
        """Get learned patterns summary"""
        return {
            "sequences": self.storage.get_sequences(min_count=2)[:20],
            "time_patterns": self.storage.get_time_patterns()[:20],
            "cooccurrences": self.storage.get_cooccurrences(min_count=2)[:20]
        }

    def get_insights(self) -> List[Dict]:
        """Generate insights from patterns"""
        insights = []

        # Most used apps
        time_patterns = self.storage.get_time_patterns()
        app_usage = defaultdict(int)
        for p in time_patterns:
            app_usage[p["app_name"]] += p["count"]

        top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_apps:
            insights.append({
                "type": "top_apps",
                "title": "Most Used Apps",
                "data": [{"app": app, "usage": count} for app, count in top_apps]
            })

        # Strongest sequences
        sequences = self.storage.get_sequences(min_count=5)[:5]
        if sequences:
            insights.append({
                "type": "strong_sequences",
                "title": "Workflow Patterns",
                "data": [
                    {
                        "from": s["from_app"],
                        "to": s["to_app"],
                        "count": s["count"]
                    }
                    for s in sequences
                ]
            })

        # Peak hours
        hour_usage = defaultdict(int)
        for p in time_patterns:
            hour_usage[p["hour"]] += p["count"]

        peak_hours = sorted(hour_usage.items(), key=lambda x: x[1], reverse=True)[:3]
        if peak_hours:
            insights.append({
                "type": "peak_hours",
                "title": "Most Active Hours",
                "data": [{"hour": h, "activity": c} for h, c in peak_hours]
            })

        return insights

    def prepare_workspace(self, apps: List[str]) -> Dict:
        """Prepare workspace by pre-launching apps"""
        launched = []
        failed = []

        for app in apps:
            try:
                subprocess.Popen(
                    [app],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                launched.append(app)
            except Exception as e:
                failed.append({"app": app, "error": str(e)})

        return {
            "launched": launched,
            "failed": failed
        }

    async def ai_analyze(self, query: str) -> Dict:
        """Use AI to analyze patterns and answer questions"""
        patterns = self.get_patterns()
        insights = self.get_insights()
        stats = self.storage.get_stats()

        context = f"""
You are Purma Cortex, the predictive AI for PurmaLinux.
You have learned from {stats['total_events']} app usage events.

Current patterns:
- {len(patterns['sequences'])} app sequences learned
- {len(patterns['time_patterns'])} time patterns learned
- {len(patterns['cooccurrences'])} co-occurrence patterns learned

Top insights:
{json.dumps(insights, indent=2)}

User question: {query}

Provide helpful insights based on the learned patterns.
"""

        # This would call Ollama in the actual implementation
        return {
            "query": query,
            "context_used": True,
            "response": "Analysis based on your usage patterns...",
            "patterns_count": stats
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════

_cortex_engine = None

def get_cortex_engine() -> CortexEngine:
    global _cortex_engine
    if _cortex_engine is None:
        _cortex_engine = CortexEngine()
    return _cortex_engine
