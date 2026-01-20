#!/usr/bin/env python3
"""
PurmaLinux - Purma Pulse
Dashboard de Estado Mental del Sistema
Real-time system monitoring with AI-powered insights
"""

import os
import sys
import json
import asyncio
import sqlite3
import psutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
import statistics
import subprocess

# ============================================
# Configuration
# ============================================

HOME = Path.home()
PULSE_DIR = HOME / ".local" / "share" / "purma" / "pulse"
PULSE_DB = PULSE_DIR / "metrics.db"
HISTORY_HOURS = 24
SAMPLE_INTERVAL = 5  # seconds
PREDICTION_WINDOW = 60  # minutes

# Create directories
PULSE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# Enums and Data Classes
# ============================================

class HealthLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"

class MetricType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    PROCESSES = "processes"
    SWAP = "swap"

@dataclass
class SystemMetrics:
    """Current system metrics snapshot"""
    timestamp: str
    cpu_percent: float
    cpu_freq: float
    cpu_cores: int
    cpu_load_1m: float
    cpu_load_5m: float
    cpu_load_15m: float
    memory_total: int
    memory_used: int
    memory_percent: float
    memory_available: int
    swap_total: int
    swap_used: int
    swap_percent: float
    disk_total: int
    disk_used: int
    disk_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    network_sent: int
    network_recv: int
    network_connections: int
    battery_percent: Optional[float] = None
    battery_charging: Optional[bool] = None
    battery_time_left: Optional[int] = None
    temperature: Optional[float] = None
    process_count: int = 0
    top_cpu_processes: List[Dict] = field(default_factory=list)
    top_memory_processes: List[Dict] = field(default_factory=list)

@dataclass
class HealthScore:
    """System health assessment"""
    overall: int  # 0-100
    level: HealthLevel
    cpu_score: int
    memory_score: int
    disk_score: int
    network_score: int
    battery_score: Optional[int] = None
    description: str = ""
    recommendations: List[str] = field(default_factory=list)

@dataclass
class Alert:
    """System alert"""
    id: str
    severity: AlertSeverity
    metric_type: MetricType
    title: str
    message: str
    value: float
    threshold: float
    timestamp: str
    acknowledged: bool = False
    auto_dismiss: bool = True

@dataclass
class Prediction:
    """Metric prediction"""
    metric_type: MetricType
    current_value: float
    predicted_value: float
    time_horizon: int  # minutes
    trend: str  # rising, falling, stable
    confidence: float
    warning: Optional[str] = None

@dataclass
class AIInsight:
    """AI-generated insight"""
    category: str
    title: str
    description: str
    priority: int  # 1-5
    action: Optional[str] = None
    command: Optional[str] = None

# ============================================
# Metrics Collector
# ============================================

class MetricsCollector:
    """Collects system metrics"""

    def __init__(self):
        self.last_disk_io = None
        self.last_net_io = None
        self.last_collect_time = None

    def collect(self) -> SystemMetrics:
        """Collect current system metrics"""
        now = datetime.now()

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_current = cpu_freq.current if cpu_freq else 0
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg()

        # Memory
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()

        disk_read = 0
        disk_write = 0
        if self.last_disk_io and self.last_collect_time:
            elapsed = (now - self.last_collect_time).total_seconds()
            if elapsed > 0:
                disk_read = int((disk_io.read_bytes - self.last_disk_io.read_bytes) / elapsed)
                disk_write = int((disk_io.write_bytes - self.last_disk_io.write_bytes) / elapsed)

        self.last_disk_io = disk_io

        # Network
        net_io = psutil.net_io_counters()
        net_connections = len(psutil.net_connections())

        net_sent = 0
        net_recv = 0
        if self.last_net_io and self.last_collect_time:
            elapsed = (now - self.last_collect_time).total_seconds()
            if elapsed > 0:
                net_sent = int((net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed)
                net_recv = int((net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed)

        self.last_net_io = net_io
        self.last_collect_time = now

        # Battery
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else None
        battery_charging = battery.power_plugged if battery else None
        battery_time = battery.secsleft if battery and battery.secsleft > 0 else None

        # Temperature (Linux specific)
        temperature = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > 0:
                            temperature = entry.current
                            break
                    if temperature:
                        break
        except:
            pass

        # Processes
        processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
        process_count = len(processes)

        # Top CPU processes
        top_cpu = sorted(
            [p.info for p in processes if p.info['cpu_percent'] is not None],
            key=lambda x: x['cpu_percent'],
            reverse=True
        )[:5]

        # Top Memory processes
        top_mem = sorted(
            [p.info for p in processes if p.info['memory_percent'] is not None],
            key=lambda x: x['memory_percent'],
            reverse=True
        )[:5]

        return SystemMetrics(
            timestamp=now.isoformat(),
            cpu_percent=cpu_percent,
            cpu_freq=cpu_freq_current,
            cpu_cores=cpu_count,
            cpu_load_1m=load_avg[0],
            cpu_load_5m=load_avg[1],
            cpu_load_15m=load_avg[2],
            memory_total=mem.total,
            memory_used=mem.used,
            memory_percent=mem.percent,
            memory_available=mem.available,
            swap_total=swap.total,
            swap_used=swap.used,
            swap_percent=swap.percent,
            disk_total=disk.total,
            disk_used=disk.used,
            disk_percent=disk.percent,
            disk_read_bytes=disk_read,
            disk_write_bytes=disk_write,
            network_sent=net_sent,
            network_recv=net_recv,
            network_connections=net_connections,
            battery_percent=battery_percent,
            battery_charging=battery_charging,
            battery_time_left=battery_time,
            temperature=temperature,
            process_count=process_count,
            top_cpu_processes=top_cpu,
            top_memory_processes=top_mem,
        )

# ============================================
# Health Analyzer
# ============================================

class HealthAnalyzer:
    """Analyzes system health and generates scores"""

    THRESHOLDS = {
        'cpu': {'excellent': 30, 'good': 50, 'fair': 70, 'poor': 85},
        'memory': {'excellent': 40, 'good': 60, 'fair': 75, 'poor': 90},
        'disk': {'excellent': 50, 'good': 70, 'fair': 85, 'poor': 95},
        'swap': {'excellent': 10, 'good': 30, 'fair': 50, 'poor': 75},
        'battery': {'excellent': 80, 'good': 50, 'fair': 25, 'poor': 10},
        'temperature': {'excellent': 50, 'good': 65, 'fair': 80, 'poor': 90},
    }

    def analyze(self, metrics: SystemMetrics) -> HealthScore:
        """Generate health score from metrics"""

        # Calculate individual scores (0-100, higher is better)
        cpu_score = self._calculate_score(metrics.cpu_percent, 'cpu')
        memory_score = self._calculate_score(metrics.memory_percent, 'memory')
        disk_score = self._calculate_score(metrics.disk_percent, 'disk')

        # Network score based on connection count and activity
        network_score = 100 if metrics.network_connections < 100 else max(0, 100 - metrics.network_connections)

        # Battery score (if available)
        battery_score = None
        if metrics.battery_percent is not None:
            battery_score = self._calculate_score(100 - metrics.battery_percent, 'battery')
            if metrics.battery_charging:
                battery_score = min(100, battery_score + 20)

        # Calculate overall score
        scores = [cpu_score, memory_score, disk_score, network_score]
        weights = [0.3, 0.3, 0.25, 0.15]

        if battery_score is not None:
            scores.append(battery_score)
            weights = [0.25, 0.25, 0.2, 0.1, 0.2]

        overall = int(sum(s * w for s, w in zip(scores, weights)))

        # Determine health level
        if overall >= 85:
            level = HealthLevel.EXCELLENT
        elif overall >= 70:
            level = HealthLevel.GOOD
        elif overall >= 50:
            level = HealthLevel.FAIR
        elif overall >= 30:
            level = HealthLevel.POOR
        else:
            level = HealthLevel.CRITICAL

        # Generate description and recommendations
        description, recommendations = self._generate_recommendations(
            metrics, cpu_score, memory_score, disk_score, battery_score
        )

        return HealthScore(
            overall=overall,
            level=level,
            cpu_score=cpu_score,
            memory_score=memory_score,
            disk_score=disk_score,
            network_score=network_score,
            battery_score=battery_score,
            description=description,
            recommendations=recommendations,
        )

    def _calculate_score(self, value: float, metric_type: str) -> int:
        """Calculate score for a metric (0-100, higher is better)"""
        thresholds = self.THRESHOLDS.get(metric_type, {'excellent': 25, 'good': 50, 'fair': 75, 'poor': 90})

        if value <= thresholds['excellent']:
            return 100
        elif value <= thresholds['good']:
            return 85 - int((value - thresholds['excellent']) / (thresholds['good'] - thresholds['excellent']) * 15)
        elif value <= thresholds['fair']:
            return 70 - int((value - thresholds['good']) / (thresholds['fair'] - thresholds['good']) * 20)
        elif value <= thresholds['poor']:
            return 50 - int((value - thresholds['fair']) / (thresholds['poor'] - thresholds['fair']) * 30)
        else:
            return max(0, 20 - int((value - thresholds['poor']) * 2))

    def _generate_recommendations(
        self,
        metrics: SystemMetrics,
        cpu_score: int,
        memory_score: int,
        disk_score: int,
        battery_score: Optional[int]
    ) -> Tuple[str, List[str]]:
        """Generate health description and recommendations"""
        issues = []
        recommendations = []

        # CPU issues
        if cpu_score < 50:
            issues.append("alto uso de CPU")
            if metrics.top_cpu_processes:
                top_proc = metrics.top_cpu_processes[0]
                recommendations.append(f"Proceso '{top_proc['name']}' usa {top_proc['cpu_percent']:.1f}% CPU")

        # Memory issues
        if memory_score < 50:
            issues.append("memoria limitada")
            if metrics.top_memory_processes:
                top_proc = metrics.top_memory_processes[0]
                recommendations.append(f"Proceso '{top_proc['name']}' usa {top_proc['memory_percent']:.1f}% RAM")
            if metrics.swap_percent > 50:
                recommendations.append("Alto uso de swap - considera agregar mas RAM")

        # Disk issues
        if disk_score < 50:
            issues.append("disco casi lleno")
            free_gb = (metrics.disk_total - metrics.disk_used) / (1024**3)
            recommendations.append(f"Solo {free_gb:.1f} GB libres en disco")
            recommendations.append("Ejecuta 'purma-pulse cleanup' para liberar espacio")

        # Battery issues
        if battery_score is not None and battery_score < 30 and not metrics.battery_charging:
            issues.append("bateria baja")
            if metrics.battery_time_left:
                mins = metrics.battery_time_left // 60
                recommendations.append(f"~{mins} minutos de bateria restante")

        # Temperature issues
        if metrics.temperature and metrics.temperature > 80:
            issues.append("temperatura elevada")
            recommendations.append(f"Temperatura: {metrics.temperature:.0f}C - revisa ventilacion")

        if not issues:
            description = "Sistema funcionando optimamente"
        elif len(issues) == 1:
            description = f"Atencion: {issues[0]}"
        else:
            description = f"Multiples alertas: {', '.join(issues)}"

        return description, recommendations

# ============================================
# Alert Manager
# ============================================

class AlertManager:
    """Manages system alerts"""

    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=100)
        self.cooldowns: Dict[str, datetime] = {}
        self.cooldown_minutes = 5

    def check_metrics(self, metrics: SystemMetrics) -> List[Alert]:
        """Check metrics and generate alerts"""
        new_alerts = []
        now = datetime.now()

        # CPU alert
        if metrics.cpu_percent > 90:
            alert = self._create_alert(
                "cpu_high", AlertSeverity.DANGER, MetricType.CPU,
                "CPU muy alto", f"Uso de CPU al {metrics.cpu_percent:.1f}%",
                metrics.cpu_percent, 90
            )
            if alert:
                new_alerts.append(alert)
        elif metrics.cpu_percent > 80:
            alert = self._create_alert(
                "cpu_warning", AlertSeverity.WARNING, MetricType.CPU,
                "CPU elevado", f"Uso de CPU al {metrics.cpu_percent:.1f}%",
                metrics.cpu_percent, 80
            )
            if alert:
                new_alerts.append(alert)

        # Memory alert
        if metrics.memory_percent > 95:
            alert = self._create_alert(
                "mem_critical", AlertSeverity.CRITICAL, MetricType.MEMORY,
                "Memoria critica", f"Memoria al {metrics.memory_percent:.1f}%",
                metrics.memory_percent, 95
            )
            if alert:
                new_alerts.append(alert)
        elif metrics.memory_percent > 85:
            alert = self._create_alert(
                "mem_high", AlertSeverity.WARNING, MetricType.MEMORY,
                "Memoria alta", f"Memoria al {metrics.memory_percent:.1f}%",
                metrics.memory_percent, 85
            )
            if alert:
                new_alerts.append(alert)

        # Disk alert
        if metrics.disk_percent > 95:
            alert = self._create_alert(
                "disk_critical", AlertSeverity.CRITICAL, MetricType.DISK,
                "Disco casi lleno", f"Disco al {metrics.disk_percent:.1f}%",
                metrics.disk_percent, 95
            )
            if alert:
                new_alerts.append(alert)
        elif metrics.disk_percent > 85:
            alert = self._create_alert(
                "disk_high", AlertSeverity.WARNING, MetricType.DISK,
                "Disco elevado", f"Disco al {metrics.disk_percent:.1f}%",
                metrics.disk_percent, 85
            )
            if alert:
                new_alerts.append(alert)

        # Battery alert
        if metrics.battery_percent is not None and not metrics.battery_charging:
            if metrics.battery_percent < 10:
                alert = self._create_alert(
                    "battery_critical", AlertSeverity.CRITICAL, MetricType.BATTERY,
                    "Bateria critica", f"Bateria al {metrics.battery_percent:.0f}%",
                    metrics.battery_percent, 10
                )
                if alert:
                    new_alerts.append(alert)
            elif metrics.battery_percent < 20:
                alert = self._create_alert(
                    "battery_low", AlertSeverity.WARNING, MetricType.BATTERY,
                    "Bateria baja", f"Bateria al {metrics.battery_percent:.0f}%",
                    metrics.battery_percent, 20
                )
                if alert:
                    new_alerts.append(alert)

        # Temperature alert
        if metrics.temperature:
            if metrics.temperature > 90:
                alert = self._create_alert(
                    "temp_critical", AlertSeverity.CRITICAL, MetricType.TEMPERATURE,
                    "Temperatura critica", f"CPU a {metrics.temperature:.0f}C",
                    metrics.temperature, 90
                )
                if alert:
                    new_alerts.append(alert)
            elif metrics.temperature > 80:
                alert = self._create_alert(
                    "temp_high", AlertSeverity.WARNING, MetricType.TEMPERATURE,
                    "Temperatura alta", f"CPU a {metrics.temperature:.0f}C",
                    metrics.temperature, 80
                )
                if alert:
                    new_alerts.append(alert)

        # Swap alert
        if metrics.swap_percent > 75:
            alert = self._create_alert(
                "swap_high", AlertSeverity.WARNING, MetricType.SWAP,
                "Alto uso de swap", f"Swap al {metrics.swap_percent:.1f}%",
                metrics.swap_percent, 75
            )
            if alert:
                new_alerts.append(alert)

        return new_alerts

    def _create_alert(
        self,
        alert_id: str,
        severity: AlertSeverity,
        metric_type: MetricType,
        title: str,
        message: str,
        value: float,
        threshold: float
    ) -> Optional[Alert]:
        """Create alert if not in cooldown"""
        now = datetime.now()

        # Check cooldown
        if alert_id in self.cooldowns:
            if now - self.cooldowns[alert_id] < timedelta(minutes=self.cooldown_minutes):
                return None

        self.cooldowns[alert_id] = now

        alert = Alert(
            id=alert_id,
            severity=severity,
            metric_type=metric_type,
            title=title,
            message=message,
            value=value,
            threshold=threshold,
            timestamp=now.isoformat(),
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        return alert

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            return True
        return False

    def dismiss(self, alert_id: str) -> bool:
        """Dismiss an alert"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())

# ============================================
# Prediction Engine
# ============================================

class PredictionEngine:
    """Predicts future metric values"""

    def __init__(self):
        self.history: Dict[str, deque] = {
            'cpu': deque(maxlen=720),      # 1 hour at 5s intervals
            'memory': deque(maxlen=720),
            'disk': deque(maxlen=720),
            'network': deque(maxlen=720),
        }

    def add_sample(self, metrics: SystemMetrics):
        """Add a metrics sample to history"""
        self.history['cpu'].append(metrics.cpu_percent)
        self.history['memory'].append(metrics.memory_percent)
        self.history['disk'].append(metrics.disk_percent)
        self.history['network'].append(metrics.network_recv + metrics.network_sent)

    def predict(self, metric_type: str, minutes: int = 30) -> Optional[Prediction]:
        """Predict future value of a metric"""
        if metric_type not in self.history:
            return None

        data = list(self.history[metric_type])
        if len(data) < 12:  # Need at least 1 minute of data
            return None

        # Calculate trend using linear regression
        n = len(data)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(data)

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(data))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Predict future value
        samples_ahead = (minutes * 60) / SAMPLE_INTERVAL
        predicted = data[-1] + slope * samples_ahead

        # Determine trend
        if abs(slope) < 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "rising"
        else:
            trend = "falling"

        # Calculate confidence based on variance
        if len(data) > 1:
            variance = statistics.variance(data)
            confidence = max(0.3, min(0.95, 1 - (variance / 1000)))
        else:
            confidence = 0.5

        # Generate warning if needed
        warning = None
        metric_enum = MetricType[metric_type.upper()]

        if metric_type == 'disk' and predicted > 95:
            warning = f"Disco podria llenarse en ~{minutes} minutos"
        elif metric_type == 'memory' and predicted > 95:
            warning = f"Memoria podria agotarse en ~{minutes} minutos"
        elif metric_type == 'cpu' and predicted > 95:
            warning = f"CPU podria saturarse"

        return Prediction(
            metric_type=metric_enum,
            current_value=data[-1],
            predicted_value=max(0, min(100, predicted)),
            time_horizon=minutes,
            trend=trend,
            confidence=confidence,
            warning=warning,
        )

    def get_all_predictions(self, minutes: int = 30) -> List[Prediction]:
        """Get predictions for all metrics"""
        predictions = []
        for metric_type in ['cpu', 'memory', 'disk']:
            pred = self.predict(metric_type, minutes)
            if pred:
                predictions.append(pred)
        return predictions

# ============================================
# AI Insights Generator
# ============================================

class InsightsGenerator:
    """Generates AI-powered insights"""

    def __init__(self, ollama_host: str = "http://127.0.0.1:11434"):
        self.ollama_host = ollama_host
        self.last_insights: List[AIInsight] = []
        self.last_generation = None
        self.cache_minutes = 5

    async def generate_insights(
        self,
        metrics: SystemMetrics,
        health: HealthScore,
        predictions: List[Prediction],
        alerts: List[Alert]
    ) -> List[AIInsight]:
        """Generate AI insights from current state"""

        # Check cache
        now = datetime.now()
        if self.last_generation and now - self.last_generation < timedelta(minutes=self.cache_minutes):
            return self.last_insights

        insights = []

        # Generate insights based on current state
        # (These are heuristic-based, can be enhanced with actual LLM calls)

        # CPU insights
        if metrics.cpu_percent > 70:
            top_proc = metrics.top_cpu_processes[0] if metrics.top_cpu_processes else None
            if top_proc:
                insights.append(AIInsight(
                    category="performance",
                    title="Proceso consumiendo CPU",
                    description=f"'{top_proc['name']}' esta usando {top_proc['cpu_percent']:.1f}% del CPU. "
                               f"Considera cerrar esta aplicacion si no la necesitas.",
                    priority=3 if metrics.cpu_percent > 85 else 2,
                    action="Ver procesos",
                    command="htop",
                ))

        # Memory insights
        if metrics.memory_percent > 75:
            available_gb = metrics.memory_available / (1024**3)
            insights.append(AIInsight(
                category="memory",
                title="Optimiza el uso de memoria",
                description=f"Solo {available_gb:.1f} GB disponibles. "
                           f"Cierra pestanas del navegador o aplicaciones no usadas.",
                priority=3 if metrics.memory_percent > 85 else 2,
            ))

            if metrics.swap_percent > 30:
                insights.append(AIInsight(
                    category="memory",
                    title="Alto uso de swap",
                    description="El sistema esta usando swap, lo que puede ralentizar el rendimiento. "
                               "Considera agregar mas RAM o cerrar aplicaciones.",
                    priority=4,
                ))

        # Disk insights
        if metrics.disk_percent > 70:
            free_gb = (metrics.disk_total - metrics.disk_used) / (1024**3)
            insights.append(AIInsight(
                category="storage",
                title="Libera espacio en disco",
                description=f"Solo {free_gb:.1f} GB libres. Limpia cache, logs y archivos temporales.",
                priority=4 if metrics.disk_percent > 85 else 2,
                action="Limpiar sistema",
                command="sudo apt autoremove && sudo apt clean",
            ))

        # Battery insights
        if metrics.battery_percent is not None:
            if metrics.battery_percent < 30 and not metrics.battery_charging:
                insights.append(AIInsight(
                    category="battery",
                    title="Conecta el cargador",
                    description=f"Bateria al {metrics.battery_percent:.0f}%. "
                               f"Conecta el cargador o activa modo ahorro de energia.",
                    priority=4,
                    action="Modo ahorro",
                    command="powerprofilesctl set power-saver",
                ))

        # Prediction-based insights
        for pred in predictions:
            if pred.warning:
                insights.append(AIInsight(
                    category="prediction",
                    title=f"Prediccion: {pred.metric_type.value}",
                    description=pred.warning,
                    priority=4,
                ))

        # Network insights
        if metrics.network_connections > 200:
            insights.append(AIInsight(
                category="network",
                title="Muchas conexiones activas",
                description=f"{metrics.network_connections} conexiones de red. "
                           f"Revisa si hay aplicaciones usando demasiada red.",
                priority=2,
                action="Ver conexiones",
                command="ss -tunap | head -20",
            ))

        # General health insight
        if health.level in (HealthLevel.POOR, HealthLevel.CRITICAL):
            insights.append(AIInsight(
                category="health",
                title="Sistema bajo estres",
                description=health.description + ". " + "; ".join(health.recommendations[:2]),
                priority=5,
            ))

        # Sort by priority
        insights.sort(key=lambda x: -x.priority)

        self.last_insights = insights
        self.last_generation = now

        return insights

# ============================================
# Metrics Storage
# ============================================

class MetricsStorage:
    """Stores historical metrics in SQLite"""

    def __init__(self, db_path: Path = PULSE_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    swap_percent REAL,
                    network_recv INTEGER,
                    network_sent INTEGER,
                    battery_percent REAL,
                    temperature REAL,
                    health_score INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON metrics(timestamp)
            """)
            conn.commit()

    def save(self, metrics: SystemMetrics, health_score: int):
        """Save metrics snapshot"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO metrics (
                    timestamp, cpu_percent, memory_percent, disk_percent,
                    swap_percent, network_recv, network_sent,
                    battery_percent, temperature, health_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp,
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.disk_percent,
                metrics.swap_percent,
                metrics.network_recv,
                metrics.network_sent,
                metrics.battery_percent,
                metrics.temperature,
                health_score,
            ))
            conn.commit()

    def get_history(self, hours: int = 1) -> List[Dict]:
        """Get historical metrics"""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM metrics
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """, (since,))

            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old(self, hours: int = HISTORY_HOURS):
        """Remove old metrics"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
            conn.commit()

# ============================================
# Main Pulse Engine
# ============================================

class PulseEngine:
    """Main Purma Pulse engine"""

    def __init__(self):
        self.collector = MetricsCollector()
        self.analyzer = HealthAnalyzer()
        self.alert_manager = AlertManager()
        self.prediction_engine = PredictionEngine()
        self.insights_generator = InsightsGenerator()
        self.storage = MetricsStorage()

        self.current_metrics: Optional[SystemMetrics] = None
        self.current_health: Optional[HealthScore] = None
        self.running = False

    def collect_now(self) -> Tuple[SystemMetrics, HealthScore]:
        """Collect metrics and analyze health"""
        self.current_metrics = self.collector.collect()
        self.current_health = self.analyzer.analyze(self.current_metrics)
        self.prediction_engine.add_sample(self.current_metrics)

        # Save to storage
        self.storage.save(self.current_metrics, self.current_health.overall)

        return self.current_metrics, self.current_health

    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        if not self.current_metrics:
            self.collect_now()

        alerts = self.alert_manager.check_metrics(self.current_metrics)

        return {
            "timestamp": self.current_metrics.timestamp,
            "health": {
                "overall": self.current_health.overall,
                "level": self.current_health.level.value,
                "description": self.current_health.description,
            },
            "metrics": {
                "cpu": {
                    "percent": self.current_metrics.cpu_percent,
                    "score": self.current_health.cpu_score,
                    "cores": self.current_metrics.cpu_cores,
                    "load": self.current_metrics.cpu_load_1m,
                },
                "memory": {
                    "percent": self.current_metrics.memory_percent,
                    "score": self.current_health.memory_score,
                    "used_gb": self.current_metrics.memory_used / (1024**3),
                    "total_gb": self.current_metrics.memory_total / (1024**3),
                },
                "disk": {
                    "percent": self.current_metrics.disk_percent,
                    "score": self.current_health.disk_score,
                    "used_gb": self.current_metrics.disk_used / (1024**3),
                    "total_gb": self.current_metrics.disk_total / (1024**3),
                },
                "network": {
                    "score": self.current_health.network_score,
                    "recv_rate": self.current_metrics.network_recv,
                    "sent_rate": self.current_metrics.network_sent,
                    "connections": self.current_metrics.network_connections,
                },
                "battery": {
                    "percent": self.current_metrics.battery_percent,
                    "charging": self.current_metrics.battery_charging,
                    "time_left": self.current_metrics.battery_time_left,
                } if self.current_metrics.battery_percent is not None else None,
                "temperature": self.current_metrics.temperature,
                "processes": self.current_metrics.process_count,
            },
            "alerts": [
                {
                    "id": a.id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                }
                for a in self.alert_manager.get_active_alerts()
            ],
            "new_alerts": [
                {
                    "id": a.id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                }
                for a in alerts
            ],
        }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics including top processes"""
        if not self.current_metrics:
            self.collect_now()

        return {
            "timestamp": self.current_metrics.timestamp,
            "cpu": {
                "percent": self.current_metrics.cpu_percent,
                "frequency": self.current_metrics.cpu_freq,
                "cores": self.current_metrics.cpu_cores,
                "load_1m": self.current_metrics.cpu_load_1m,
                "load_5m": self.current_metrics.cpu_load_5m,
                "load_15m": self.current_metrics.cpu_load_15m,
                "top_processes": self.current_metrics.top_cpu_processes,
            },
            "memory": {
                "percent": self.current_metrics.memory_percent,
                "total": self.current_metrics.memory_total,
                "used": self.current_metrics.memory_used,
                "available": self.current_metrics.memory_available,
                "swap_percent": self.current_metrics.swap_percent,
                "swap_used": self.current_metrics.swap_used,
                "top_processes": self.current_metrics.top_memory_processes,
            },
            "disk": {
                "percent": self.current_metrics.disk_percent,
                "total": self.current_metrics.disk_total,
                "used": self.current_metrics.disk_used,
                "read_rate": self.current_metrics.disk_read_bytes,
                "write_rate": self.current_metrics.disk_write_bytes,
            },
            "network": {
                "recv_rate": self.current_metrics.network_recv,
                "sent_rate": self.current_metrics.network_sent,
                "connections": self.current_metrics.network_connections,
            },
            "battery": {
                "percent": self.current_metrics.battery_percent,
                "charging": self.current_metrics.battery_charging,
                "time_left": self.current_metrics.battery_time_left,
            } if self.current_metrics.battery_percent is not None else None,
            "temperature": self.current_metrics.temperature,
            "process_count": self.current_metrics.process_count,
        }

    def get_predictions(self, minutes: int = 30) -> List[Dict]:
        """Get metric predictions"""
        predictions = self.prediction_engine.get_all_predictions(minutes)
        return [
            {
                "metric": p.metric_type.value,
                "current": p.current_value,
                "predicted": p.predicted_value,
                "trend": p.trend,
                "confidence": p.confidence,
                "warning": p.warning,
                "time_horizon": p.time_horizon,
            }
            for p in predictions
        ]

    async def get_insights(self) -> List[Dict]:
        """Get AI insights"""
        if not self.current_metrics or not self.current_health:
            self.collect_now()

        predictions = self.prediction_engine.get_all_predictions()
        alerts = self.alert_manager.get_active_alerts()

        insights = await self.insights_generator.generate_insights(
            self.current_metrics,
            self.current_health,
            predictions,
            alerts,
        )

        return [
            {
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "priority": i.priority,
                "action": i.action,
                "command": i.command,
            }
            for i in insights
        ]

    def get_history(self, hours: int = 1) -> List[Dict]:
        """Get historical metrics"""
        return self.storage.get_history(hours)

    def cleanup_disk(self) -> Dict[str, Any]:
        """Run disk cleanup commands"""
        results = []
        freed = 0

        # Clean apt cache
        try:
            result = subprocess.run(
                ["sudo", "apt", "clean"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                results.append("APT cache limpiado")
        except:
            pass

        # Clean journal logs
        try:
            result = subprocess.run(
                ["sudo", "journalctl", "--vacuum-time=3d"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                results.append("Logs de journal limpiados")
        except:
            pass

        # Clean user cache
        try:
            cache_dir = HOME / ".cache"
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    if item.is_dir() and item.name.startswith("thumbnails"):
                        subprocess.run(["rm", "-rf", str(item)], timeout=30)
                results.append("Cache de thumbnails limpiado")
        except:
            pass

        # Get new disk usage
        disk = psutil.disk_usage('/')

        return {
            "success": True,
            "actions": results,
            "disk_percent": disk.percent,
            "free_gb": (disk.total - disk.used) / (1024**3),
        }


# Global instance
pulse_engine = PulseEngine()
