/**
 * PurmaLinux - Bridge Widget
 * AI-augmented terminal interface
 */

const PURMA_SERVER = "http://localhost:8787";

// ============================================
// State Management
// ============================================

const BridgeState = Variable({
  history: [],
  suggestions: [],
  analysis: null,
  explanation: null,
  loading: false,
  error: null,
});

const popupVisible = Variable(false);
const inputText = Variable("");
const currentView = Variable("main"); // main, analysis, history

// ============================================
// Risk Level Colors
// ============================================

const RISK_COLORS = {
  safe: "#3fb950",
  low: "#58a6ff",
  medium: "#d29922",
  high: "#f85149",
  critical: "#ff7b72",
};

const RISK_ICONS = {
  safe: "",
  low: "",
  medium: "",
  high: "",
  critical: "",
};

// ============================================
// API Functions
// ============================================

async function translateCommand(query) {
  if (!query || !query.trim()) return;

  BridgeState.value = { ...BridgeState.value, loading: true, error: null };
  inputText.value = "";

  try {
    const result = await Utils.execAsync([
      "curl", "-s",
      `${PURMA_SERVER}/bridge/translate?text=${encodeURIComponent(query)}`,
    ]);
    const data = JSON.parse(result);

    BridgeState.value = {
      ...BridgeState.value,
      suggestions: data.suggestions || [],
      loading: false,
    };

    if (data.suggestions && data.suggestions.length > 0) {
      // Auto-analyze the top suggestion
      await analyzeCommand(data.suggestions[0].command);
    }
  } catch (e) {
    BridgeState.value = {
      ...BridgeState.value,
      loading: false,
      error: "Error al traducir",
    };
  }
}

async function analyzeCommand(command) {
  if (!command) return;

  try {
    const result = await Utils.execAsync([
      "curl", "-s",
      `${PURMA_SERVER}/bridge/analyze?command=${encodeURIComponent(command)}`,
    ]);
    const data = JSON.parse(result);

    BridgeState.value = {
      ...BridgeState.value,
      analysis: data.analysis || null,
    };
  } catch (e) {
    console.log("Error analyzing command:", e);
  }
}

async function explainError(error) {
  BridgeState.value = { ...BridgeState.value, loading: true };

  try {
    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      "-H", "Content-Type: application/json",
      "-d", JSON.stringify({ command: "", error: error, exit_code: 1 }),
      `${PURMA_SERVER}/bridge/explain`,
    ]);
    const data = JSON.parse(result);

    BridgeState.value = {
      ...BridgeState.value,
      explanation: data.explanation || null,
      loading: false,
    };
    currentView.value = "explanation";
  } catch (e) {
    BridgeState.value = {
      ...BridgeState.value,
      loading: false,
      error: "Error al explicar",
    };
  }
}

async function fetchHistory() {
  try {
    const result = await Utils.execAsync([
      "curl", "-s",
      `${PURMA_SERVER}/bridge/history?limit=20`,
    ]);
    const data = JSON.parse(result);

    BridgeState.value = {
      ...BridgeState.value,
      history: data.entries || [],
    };
  } catch (e) {
    console.log("Error fetching history:", e);
  }
}

async function copyToClipboard(text) {
  await Utils.execAsync(["wl-copy", text]);
  Utils.execAsync([
    "notify-send", "-i", "edit-copy",
    "Purma Bridge",
    "Comando copiado al portapapeles",
  ]);
}

async function runInTerminal(command) {
  // Open terminal with command
  await Utils.execAsync([
    "kitty", "-e", "bash", "-c",
    `echo '$ ${command}'; ${command}; echo ''; echo 'Presiona Enter para cerrar'; read`,
  ]);
}

// ============================================
// Widget Components
// ============================================

function RiskBadge(risk) {
  return Widget.Box({
    class_name: `risk-badge risk-${risk}`,
    children: [
      Widget.Label({
        label: RISK_ICONS[risk] || "",
        class_name: "risk-icon",
      }),
      Widget.Label({
        label: risk.toUpperCase(),
        class_name: "risk-label",
      }),
    ],
  });
}

function SuggestionItem(suggestion, index) {
  const { command, description, confidence, source } = suggestion;
  const confPercent = Math.round(confidence * 100);

  return Widget.Button({
    class_name: "suggestion-item",
    on_clicked: () => copyToClipboard(command),
    on_secondary_click: () => runInTerminal(command),
    child: Widget.Box({
      vertical: true,
      spacing: 4,
      children: [
        Widget.Box({
          children: [
            Widget.Label({
              class_name: "suggestion-num",
              label: `${index + 1}`,
            }),
            Widget.Label({
              class_name: "suggestion-command",
              label: command,
              xalign: 0,
              hexpand: true,
              max_width_chars: 40,
              truncate: "end",
            }),
            Widget.Label({
              class_name: "suggestion-confidence",
              label: `${confPercent}%`,
            }),
          ],
        }),
        Widget.Box({
          children: [
            Widget.Label({
              class_name: "suggestion-source",
              label: source === "ai" ? "" : "",
            }),
            Widget.Label({
              class_name: "suggestion-desc",
              label: description || "",
              xalign: 0,
              hexpand: true,
              max_width_chars: 50,
              truncate: "end",
            }),
          ],
        }),
      ],
    }),
  });
}

function AnalysisPanel() {
  return Widget.Box({
    class_name: "analysis-panel",
    vertical: true,
    spacing: 8,
    setup: (self) => {
      self.hook(BridgeState, () => {
        const { analysis } = BridgeState.value;

        if (!analysis) {
          self.visible = false;
          return;
        }

        self.visible = true;
        self.children = [
          Widget.Box({
            class_name: "analysis-header",
            children: [
              Widget.Label({
                label: " Analisis de Seguridad",
                class_name: "analysis-title",
                xalign: 0,
                hexpand: true,
              }),
              RiskBadge(analysis.risk || "safe"),
            ],
          }),
          Widget.Label({
            class_name: "analysis-desc",
            label: analysis.description || "",
            xalign: 0,
            wrap: true,
          }),
          ...((analysis.warnings || []).length > 0
            ? [
                Widget.Box({
                  class_name: "analysis-warnings",
                  vertical: true,
                  spacing: 4,
                  children: [
                    Widget.Label({
                      class_name: "warnings-title",
                      label: " Advertencias:",
                      xalign: 0,
                    }),
                    ...analysis.warnings.map((w) =>
                      Widget.Label({
                        class_name: "warning-item",
                        label: `  ${w}`,
                        xalign: 0,
                        wrap: true,
                      })
                    ),
                  ],
                }),
              ]
            : []),
        ];
      });
    },
  });
}

function SuggestionsList() {
  return Widget.Box({
    class_name: "suggestions-list",
    vertical: true,
    spacing: 4,
    setup: (self) => {
      self.hook(BridgeState, () => {
        const { suggestions, loading, error } = BridgeState.value;

        if (loading) {
          self.children = [
            Widget.Box({
              class_name: "suggestions-loading",
              hpack: "center",
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "loading-spinner" }),
                Widget.Label({ label: "Traduciendo..." }),
              ],
            }),
          ];
          return;
        }

        if (error) {
          self.children = [
            Widget.Box({
              class_name: "suggestions-error",
              hpack: "center",
              children: [
                Widget.Label({ label: "", class_name: "error-icon" }),
                Widget.Label({ label: error }),
              ],
            }),
          ];
          return;
        }

        if (suggestions.length === 0) {
          self.children = [
            Widget.Box({
              class_name: "suggestions-empty",
              vertical: true,
              hpack: "center",
              vpack: "center",
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({
                  label: "Escribe lo que quieres hacer",
                  class_name: "empty-text",
                }),
                Widget.Label({
                  label: 'Ejemplo: "mostrar archivos grandes"',
                  class_name: "empty-hint",
                }),
              ],
            }),
          ];
          return;
        }

        self.children = suggestions.map((s, i) => SuggestionItem(s, i));
      });
    },
  });
}

function HistoryItem(entry) {
  const riskColor = RISK_COLORS[entry.risk_level] || RISK_COLORS.safe;

  return Widget.Button({
    class_name: "history-item",
    on_clicked: () => copyToClipboard(entry.command),
    child: Widget.Box({
      spacing: 8,
      children: [
        Widget.Box({
          class_name: "history-status",
          css: `background: ${entry.success ? "#3fb950" : "#f85149"};`,
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "history-command",
              label: entry.command,
              xalign: 0,
              max_width_chars: 40,
              truncate: "end",
            }),
            Widget.Box({
              spacing: 8,
              children: [
                Widget.Label({
                  class_name: "history-intent",
                  label: entry.intent || "",
                  xalign: 0,
                  max_width_chars: 30,
                  truncate: "end",
                }),
                Widget.Label({
                  class_name: "history-time",
                  label: formatTime(entry.timestamp),
                }),
              ],
            }),
          ],
        }),
        Widget.Label({
          class_name: `history-risk risk-${entry.risk_level}`,
          label: RISK_ICONS[entry.risk_level] || "",
        }),
      ],
    }),
  });
}

function formatTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const diff = (now - date) / 1000;

  if (diff < 60) return "ahora";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return date.toLocaleDateString();
}

function HistoryView() {
  return Widget.Box({
    class_name: "history-view",
    vertical: true,
    spacing: 4,
    setup: (self) => {
      self.hook(BridgeState, () => {
        const { history } = BridgeState.value;

        if (history.length === 0) {
          self.children = [
            Widget.Box({
              class_name: "history-empty",
              vertical: true,
              hpack: "center",
              vpack: "center",
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({
                  label: "Sin historial",
                  class_name: "empty-text",
                }),
              ],
            }),
          ];
          return;
        }

        self.children = history.slice(0, 10).map((e) => HistoryItem(e));
      });
    },
  });
}

function InputBar() {
  return Widget.Box({
    class_name: "input-bar",
    spacing: 8,
    children: [
      Widget.Label({
        label: "??",
        class_name: "input-prompt",
      }),
      Widget.Entry({
        class_name: "input-entry",
        placeholder_text: "Describe lo que quieres hacer...",
        hexpand: true,
        text: inputText.bind(),
        on_change: ({ text }) => (inputText.value = text),
        on_accept: () => translateCommand(inputText.value),
      }),
      Widget.Button({
        class_name: "input-send",
        child: Widget.Label(""),
        on_clicked: () => translateCommand(inputText.value),
        sensitive: inputText.bind().transform((t) => t.length > 0),
      }),
    ],
  });
}

function BridgeHeader() {
  return Widget.Box({
    class_name: "bridge-header",
    children: [
      Widget.Label({
        class_name: "bridge-title",
        label: " Purma Bridge",
        hexpand: true,
        xalign: 0,
      }),
      Widget.Button({
        class_name: "header-btn history-btn",
        child: Widget.Label(""),
        on_clicked: () => {
          if (currentView.value === "history") {
            currentView.value = "main";
          } else {
            fetchHistory();
            currentView.value = "history";
          }
        },
        tooltip_text: "Historial",
      }),
      Widget.Button({
        class_name: "header-btn terminal-btn",
        child: Widget.Label(""),
        on_clicked: () => {
          Utils.execAsync(["kitty", "-e", "purma-bridge"]);
          popupVisible.value = false;
        },
        tooltip_text: "Abrir terminal Bridge",
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label(""),
        on_clicked: () => (popupVisible.value = false),
      }),
    ],
  });
}

function QuickActions() {
  const actions = [
    { icon: "", label: "Archivos grandes", query: "encontrar archivos grandes" },
    { icon: "", label: "Uso de disco", query: "mostrar uso de disco" },
    { icon: "", label: "Procesos", query: "mostrar procesos activos" },
    { icon: "", label: "Red", query: "mostrar conexiones de red" },
  ];

  return Widget.Box({
    class_name: "quick-actions",
    spacing: 4,
    homogeneous: true,
    children: actions.map((a) =>
      Widget.Button({
        class_name: "quick-action",
        child: Widget.Box({
          vertical: true,
          spacing: 2,
          children: [
            Widget.Label({ label: a.icon, class_name: "quick-icon" }),
            Widget.Label({ label: a.label, class_name: "quick-label" }),
          ],
        }),
        on_clicked: () => {
          inputText.value = a.query;
          translateCommand(a.query);
        },
      })
    ),
  });
}

function MainView() {
  return Widget.Box({
    vertical: true,
    children: [
      InputBar(),
      QuickActions(),
      Widget.Scrollable({
        class_name: "suggestions-scroll",
        hscroll: "never",
        vscroll: "automatic",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          spacing: 8,
          children: [SuggestionsList(), AnalysisPanel()],
        }),
      }),
    ],
  });
}

function BridgePopup() {
  return Widget.Box({
    class_name: "bridge-popup",
    vertical: true,
    children: [
      BridgeHeader(),
      Widget.Stack({
        class_name: "bridge-content",
        transition: "slide_left_right",
        shown: currentView.bind(),
        children: {
          main: MainView(),
          history: Widget.Box({
            vertical: true,
            children: [
              Widget.Box({
                class_name: "view-header",
                children: [
                  Widget.Button({
                    class_name: "back-btn",
                    child: Widget.Label(" Volver"),
                    on_clicked: () => (currentView.value = "main"),
                  }),
                  Widget.Label({
                    class_name: "view-title",
                    label: "Historial de comandos",
                    hexpand: true,
                    xalign: 0,
                  }),
                ],
              }),
              Widget.Scrollable({
                class_name: "history-scroll",
                hscroll: "never",
                vscroll: "automatic",
                vexpand: true,
                child: HistoryView(),
              }),
            ],
          }),
        },
      }),
    ],
  });
}

// ============================================
// Bar Widget
// ============================================

function BridgeButton() {
  return Widget.Button({
    class_name: "bridge-button",
    on_clicked: () => {
      popupVisible.value = !popupVisible.value;
      if (popupVisible.value) {
        currentView.value = "main";
      }
    },
    tooltip_text: "Purma Bridge - Terminal IA",
    child: Widget.Box({
      spacing: 6,
      children: [
        Widget.Label({
          class_name: "bridge-btn-icon",
          label: "",
        }),
        Widget.Label({
          class_name: "bridge-btn-label",
          label: "Bridge",
        }),
      ],
    }),
  });
}

// ============================================
// Main Window
// ============================================

function BridgeWindow() {
  return Widget.Window({
    name: "bridge-popup",
    class_name: "bridge-window",
    anchor: ["top", "right"],
    margins: [40, 10, 0, 0],
    visible: popupVisible.bind(),
    keymode: "on-demand",
    child: BridgePopup(),
    setup: (self) => {
      self.keybind("Escape", () => (popupVisible.value = false));
    },
  });
}

// ============================================
// Toggle Functions
// ============================================

function toggleBridge() {
  popupVisible.value = !popupVisible.value;
  if (popupVisible.value) {
    currentView.value = "main";
  }
}

// Export
export {
  BridgeWindow,
  BridgeButton,
  toggleBridge,
  translateCommand,
  analyzeCommand,
  fetchHistory,
};
