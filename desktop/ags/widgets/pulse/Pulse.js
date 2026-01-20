/**
 * PurmaLinux - Pulse Widget
 * System health dashboard
 */

const PURMA_SERVER = "http://localhost:8787";
const REFRESH_INTERVAL = 5000; // 5 seconds

// ============================================
// State Management
// ============================================

const PulseState = Variable({
  health: {
    overall: 0,
    level: "unknown",
    description: "",
  },
  metrics: {
    cpu: { percent: 0, score: 0 },
    memory: { percent: 0, score: 0, used_gb: 0, total_gb: 0 },
    disk: { percent: 0, score: 0, used_gb: 0, total_gb: 0 },
    network: { score: 0, connections: 0 },
    battery: null,
    temperature: null,
  },
  alerts: [],
  insights: [],
  predictions: [],
  loading: false,
  error: null,
});

const popupVisible = Variable(false);
const currentView = Variable("dashboard"); // dashboard, details, insights
let refreshTimer = null;

// ============================================
// Health Level Colors
// ============================================

const HEALTH_COLORS = {
  excellent: "#3fb950",
  good: "#58a6ff",
  fair: "#d29922",
  poor: "#f85149",
  critical: "#ff7b72",
  unknown: "#8b949e",
};

const HEALTH_ICONS = {
  excellent: "",
  good: "",
  fair: "",
  poor: "",
  critical: "",
  unknown: "",
};

// ============================================
// API Functions
// ============================================

async function fetchStatus() {
  if (PulseState.value.loading) return;

  try {
    const result = await Utils.execAsync([
      "curl", "-s", `${PURMA_SERVER}/pulse/status`,
    ]);
    const data = JSON.parse(result);

    PulseState.value = {
      ...PulseState.value,
      health: data.health || PulseState.value.health,
      metrics: data.metrics || PulseState.value.metrics,
      alerts: data.alerts || [],
      error: null,
    };

    // Show notification for new critical alerts
    for (const alert of data.new_alerts || []) {
      if (alert.severity === "critical" || alert.severity === "danger") {
        Utils.execAsync([
          "notify-send", "-u", "critical",
          "-i", "dialog-warning",
          `Purma Pulse: ${alert.title}`,
          alert.message,
        ]);
      }
    }
  } catch (e) {
    PulseState.value = {
      ...PulseState.value,
      error: "Error al conectar",
    };
  }
}

async function fetchInsights() {
  try {
    const result = await Utils.execAsync([
      "curl", "-s", `${PURMA_SERVER}/pulse/insights`,
    ]);
    const data = JSON.parse(result);

    PulseState.value = {
      ...PulseState.value,
      insights: data.insights || [],
    };
  } catch (e) {
    console.log("Error fetching insights:", e);
  }
}

async function fetchPredictions() {
  try {
    const result = await Utils.execAsync([
      "curl", "-s", `${PURMA_SERVER}/pulse/predictions`,
    ]);
    const data = JSON.parse(result);

    PulseState.value = {
      ...PulseState.value,
      predictions: data.predictions || [],
    };
  } catch (e) {
    console.log("Error fetching predictions:", e);
  }
}

async function runCleanup() {
  PulseState.value = { ...PulseState.value, loading: true };

  try {
    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST", `${PURMA_SERVER}/pulse/cleanup`,
    ]);
    const data = JSON.parse(result);

    if (data.success) {
      Utils.execAsync([
        "notify-send", "-i", "emblem-ok",
        "Purma Pulse",
        `Limpieza completada. ${data.free_gb.toFixed(1)} GB libres`,
      ]);
    }

    PulseState.value = { ...PulseState.value, loading: false };
    await fetchStatus();
  } catch (e) {
    PulseState.value = { ...PulseState.value, loading: false };
  }
}

function startAutoRefresh() {
  if (refreshTimer) return;
  fetchStatus();
  refreshTimer = Utils.interval(REFRESH_INTERVAL, fetchStatus);
}

function stopAutoRefresh() {
  if (refreshTimer) {
    refreshTimer.destroy();
    refreshTimer = null;
  }
}

// ============================================
// Widget Components
// ============================================

function HealthGauge() {
  return Widget.Box({
    class_name: "health-gauge",
    vertical: true,
    hpack: "center",
    setup: (self) => {
      self.hook(PulseState, () => {
        const { health } = PulseState.value;
        const color = HEALTH_COLORS[health.level] || HEALTH_COLORS.unknown;
        const icon = HEALTH_ICONS[health.level] || HEALTH_ICONS.unknown;

        self.children = [
          Widget.Box({
            class_name: "gauge-circle",
            css: `border-color: ${color};`,
            child: Widget.Box({
              vertical: true,
              hpack: "center",
              vpack: "center",
              children: [
                Widget.Label({
                  class_name: "gauge-score",
                  label: `${health.overall}`,
                  css: `color: ${color};`,
                }),
                Widget.Label({
                  class_name: "gauge-label",
                  label: health.level.toUpperCase(),
                  css: `color: ${color};`,
                }),
              ],
            }),
          }),
          Widget.Label({
            class_name: "gauge-icon",
            label: icon,
            css: `color: ${color};`,
          }),
        ];
      });
    },
  });
}

function MetricBar(metric, label, icon, unit = "%") {
  return Widget.Box({
    class_name: "metric-bar",
    setup: (self) => {
      self.hook(PulseState, () => {
        const m = PulseState.value.metrics[metric];
        if (!m) {
          self.visible = false;
          return;
        }
        self.visible = true;

        const percent = m.percent || 0;
        const score = m.score || 0;

        // Color based on percent
        let barColor = "#3fb950";
        if (percent > 85) barColor = "#f85149";
        else if (percent > 70) barColor = "#d29922";
        else if (percent > 50) barColor = "#58a6ff";

        self.children = [
          Widget.Label({
            class_name: "metric-icon",
            label: icon,
          }),
          Widget.Box({
            vertical: true,
            hexpand: true,
            children: [
              Widget.Box({
                children: [
                  Widget.Label({
                    class_name: "metric-label",
                    label: label,
                    xalign: 0,
                    hexpand: true,
                  }),
                  Widget.Label({
                    class_name: "metric-value",
                    label: `${percent.toFixed(0)}${unit}`,
                  }),
                ],
              }),
              Widget.Box({
                class_name: "metric-bar-bg",
                child: Widget.Box({
                  class_name: "metric-bar-fill",
                  css: `min-width: ${Math.min(percent, 100)}%; background: ${barColor};`,
                }),
              }),
            ],
          }),
        ];
      });
    },
  });
}

function BatteryIndicator() {
  return Widget.Box({
    class_name: "battery-indicator",
    setup: (self) => {
      self.hook(PulseState, () => {
        const battery = PulseState.value.metrics.battery;
        if (!battery) {
          self.visible = false;
          return;
        }
        self.visible = true;

        const percent = battery.percent || 0;
        const charging = battery.charging;

        let icon = "";
        if (charging) icon = "";
        else if (percent > 80) icon = "";
        else if (percent > 60) icon = "";
        else if (percent > 40) icon = "";
        else if (percent > 20) icon = "";
        else icon = "";

        let color = "#3fb950";
        if (percent < 20) color = "#f85149";
        else if (percent < 40) color = "#d29922";

        self.children = [
          Widget.Label({
            class_name: "battery-icon",
            label: icon,
            css: `color: ${color};`,
          }),
          Widget.Label({
            class_name: "battery-percent",
            label: `${percent.toFixed(0)}%`,
          }),
        ];
      });
    },
  });
}

function AlertItem(alert) {
  const severityIcons = {
    info: "",
    warning: "",
    danger: "",
    critical: "",
  };

  const severityColors = {
    info: "#58a6ff",
    warning: "#d29922",
    danger: "#f85149",
    critical: "#ff7b72",
  };

  return Widget.Box({
    class_name: `alert-item severity-${alert.severity}`,
    spacing: 8,
    children: [
      Widget.Label({
        class_name: "alert-icon",
        label: severityIcons[alert.severity] || "",
        css: `color: ${severityColors[alert.severity] || "#8b949e"};`,
      }),
      Widget.Box({
        vertical: true,
        hexpand: true,
        children: [
          Widget.Label({
            class_name: "alert-title",
            label: alert.title,
            xalign: 0,
          }),
          Widget.Label({
            class_name: "alert-message",
            label: alert.message,
            xalign: 0,
          }),
        ],
      }),
    ],
  });
}

function AlertsPanel() {
  return Widget.Box({
    class_name: "alerts-panel",
    vertical: true,
    setup: (self) => {
      self.hook(PulseState, () => {
        const { alerts } = PulseState.value;

        if (alerts.length === 0) {
          self.visible = false;
          return;
        }

        self.visible = true;
        self.children = [
          Widget.Label({
            class_name: "panel-title",
            label: ` Alertas (${alerts.length})`,
            xalign: 0,
          }),
          ...alerts.slice(0, 3).map((a) => AlertItem(a)),
        ];
      });
    },
  });
}

function InsightItem(insight) {
  const categoryIcons = {
    performance: "",
    memory: "",
    storage: "",
    battery: "",
    network: "",
    prediction: "",
    health: "",
  };

  return Widget.Button({
    class_name: "insight-item",
    on_clicked: () => {
      if (insight.command) {
        Utils.execAsync(["kitty", "-e", "bash", "-c", insight.command]);
      }
    },
    child: Widget.Box({
      spacing: 8,
      children: [
        Widget.Label({
          class_name: "insight-icon",
          label: categoryIcons[insight.category] || "",
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "insight-title",
              label: insight.title,
              xalign: 0,
            }),
            Widget.Label({
              class_name: "insight-desc",
              label: insight.description,
              xalign: 0,
              max_width_chars: 40,
              wrap: true,
            }),
          ],
        }),
        Widget.Label({
          class_name: "insight-action",
          label: insight.command ? "" : "",
          visible: !!insight.command,
        }),
      ],
    }),
  });
}

function InsightsView() {
  return Widget.Box({
    class_name: "insights-view",
    vertical: true,
    spacing: 8,
    setup: (self) => {
      self.hook(PulseState, () => {
        const { insights } = PulseState.value;

        if (insights.length === 0) {
          self.children = [
            Widget.Box({
              class_name: "insights-empty",
              vertical: true,
              hpack: "center",
              vpack: "center",
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({
                  label: "Todo en orden",
                  class_name: "empty-text",
                }),
                Widget.Label({
                  label: "No hay recomendaciones",
                  class_name: "empty-hint",
                }),
              ],
            }),
          ];
          return;
        }

        self.children = insights.map((i) => InsightItem(i));
      });
    },
  });
}

function ProcessList(type = "cpu") {
  return Widget.Box({
    class_name: "process-list",
    vertical: true,
    setup: (self) => {
      self.hook(PulseState, () => {
        const { metrics } = PulseState.value;
        const processes = type === "cpu"
          ? metrics.cpu?.top_processes || []
          : metrics.memory?.top_processes || [];

        self.children = [
          Widget.Label({
            class_name: "process-title",
            label: type === "cpu" ? " Top CPU" : " Top Memoria",
            xalign: 0,
          }),
          ...processes.slice(0, 3).map((p) =>
            Widget.Box({
              class_name: "process-item",
              children: [
                Widget.Label({
                  class_name: "process-name",
                  label: p.name || "unknown",
                  xalign: 0,
                  hexpand: true,
                  max_width_chars: 20,
                  truncate: "end",
                }),
                Widget.Label({
                  class_name: "process-value",
                  label: `${(type === "cpu" ? p.cpu_percent : p.memory_percent || 0).toFixed(1)}%`,
                }),
              ],
            })
          ),
        ];
      });
    },
  });
}

function DashboardView() {
  return Widget.Box({
    vertical: true,
    spacing: 12,
    children: [
      HealthGauge(),
      Widget.Box({
        class_name: "metrics-grid",
        vertical: true,
        spacing: 8,
        children: [
          MetricBar("cpu", "CPU", ""),
          MetricBar("memory", "Memoria", ""),
          MetricBar("disk", "Disco", ""),
        ],
      }),
      BatteryIndicator(),
      AlertsPanel(),
    ],
  });
}

function DetailsView() {
  return Widget.Box({
    vertical: true,
    spacing: 12,
    children: [
      Widget.Box({
        spacing: 8,
        homogeneous: true,
        children: [
          ProcessList("cpu"),
          ProcessList("memory"),
        ],
      }),
      Widget.Box({
        class_name: "network-stats",
        children: [
          Widget.Label({
            class_name: "stat-icon",
            label: "",
          }),
          Widget.Label({
            class_name: "stat-label",
            label: "Red",
            hexpand: true,
            xalign: 0,
          }),
          Widget.Label({
            class_name: "stat-value",
            setup: (self) => {
              self.hook(PulseState, () => {
                const net = PulseState.value.metrics.network;
                self.label = `${net?.connections || 0} conexiones`;
              });
            },
          }),
        ],
      }),
    ],
  });
}

function PulseHeader() {
  return Widget.Box({
    class_name: "pulse-header",
    children: [
      Widget.Label({
        class_name: "pulse-title",
        label: " Purma Pulse",
        hexpand: true,
        xalign: 0,
      }),
      Widget.Button({
        class_name: "header-btn",
        child: Widget.Label(""),
        on_clicked: () => {
          if (currentView.value === "insights") {
            currentView.value = "dashboard";
          } else {
            fetchInsights();
            currentView.value = "insights";
          }
        },
        tooltip_text: "Insights",
      }),
      Widget.Button({
        class_name: "header-btn",
        child: Widget.Label(""),
        on_clicked: () => {
          if (currentView.value === "details") {
            currentView.value = "dashboard";
          } else {
            currentView.value = "details";
          }
        },
        tooltip_text: "Detalles",
      }),
      Widget.Button({
        class_name: "header-btn refresh-btn",
        child: Widget.Label(""),
        on_clicked: () => fetchStatus(),
        tooltip_text: "Actualizar",
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label(""),
        on_clicked: () => (popupVisible.value = false),
      }),
    ],
  });
}

function ActionBar() {
  return Widget.Box({
    class_name: "pulse-actions",
    spacing: 8,
    children: [
      Widget.Button({
        class_name: "action-btn cleanup",
        hexpand: true,
        child: Widget.Box({
          hpack: "center",
          spacing: 6,
          children: [
            Widget.Label(""),
            Widget.Label("Limpiar"),
          ],
        }),
        on_clicked: () => runCleanup(),
        tooltip_text: "Limpiar cache y temporales",
      }),
      Widget.Button({
        class_name: "action-btn terminal",
        hexpand: true,
        child: Widget.Box({
          hpack: "center",
          spacing: 6,
          children: [
            Widget.Label(""),
            Widget.Label("htop"),
          ],
        }),
        on_clicked: () => Utils.execAsync(["kitty", "-e", "htop"]),
        tooltip_text: "Abrir htop",
      }),
    ],
  });
}

function PulsePopup() {
  return Widget.Box({
    class_name: "pulse-popup",
    vertical: true,
    children: [
      PulseHeader(),
      Widget.Stack({
        class_name: "pulse-content",
        transition: "slide_left_right",
        shown: currentView.bind(),
        children: {
          dashboard: Widget.Scrollable({
            hscroll: "never",
            vscroll: "automatic",
            vexpand: true,
            child: DashboardView(),
          }),
          details: Widget.Scrollable({
            hscroll: "never",
            vscroll: "automatic",
            vexpand: true,
            child: DetailsView(),
          }),
          insights: Widget.Scrollable({
            hscroll: "never",
            vscroll: "automatic",
            vexpand: true,
            child: InsightsView(),
          }),
        },
      }),
      ActionBar(),
    ],
  });
}

// ============================================
// Bar Widget
// ============================================

function PulseButton() {
  return Widget.Button({
    class_name: "pulse-button",
    on_clicked: () => {
      popupVisible.value = !popupVisible.value;
      if (popupVisible.value) {
        startAutoRefresh();
        currentView.value = "dashboard";
      } else {
        stopAutoRefresh();
      }
    },
    tooltip_text: "Purma Pulse - Estado del Sistema",
    child: Widget.Box({
      spacing: 4,
      setup: (self) => {
        self.hook(PulseState, () => {
          const { health, metrics } = PulseState.value;
          const color = HEALTH_COLORS[health.level] || HEALTH_COLORS.unknown;
          const icon = HEALTH_ICONS[health.level] || "";

          self.children = [
            Widget.Label({
              class_name: "pulse-btn-icon",
              label: icon,
              css: `color: ${color};`,
            }),
            Widget.Label({
              class_name: "pulse-btn-score",
              label: `${health.overall}`,
              css: `color: ${color};`,
            }),
          ];
        });
      },
    }),
  });
}

// ============================================
// Main Window
// ============================================

function PulseWindow() {
  return Widget.Window({
    name: "pulse-popup",
    class_name: "pulse-window",
    anchor: ["top", "right"],
    margins: [40, 10, 0, 0],
    visible: popupVisible.bind(),
    keymode: "on-demand",
    child: PulsePopup(),
    setup: (self) => {
      self.keybind("Escape", () => {
        popupVisible.value = false;
        stopAutoRefresh();
      });
    },
  });
}

// ============================================
// Toggle Functions
// ============================================

function togglePulse() {
  popupVisible.value = !popupVisible.value;
  if (popupVisible.value) {
    startAutoRefresh();
    currentView.value = "dashboard";
  } else {
    stopAutoRefresh();
  }
}

// Initial fetch after a delay
Utils.timeout(2000, () => fetchStatus());

// Export
export {
  PulseWindow,
  PulseButton,
  togglePulse,
  fetchStatus,
  fetchInsights,
};
