/**
 * PurmaLinux - Brain Widget
 * Unified control for advanced AI systems:
 * - Cortex (Predictive AI)
 * - Memory (RAG)
 * - Ghost (Shadow Observer)
 * - Multi-Agent
 */

const API_BASE = "http://localhost:11435";

// State management
const brainState = Variable({
  visible: false,
  view: "overview", // overview, cortex, memory, ghost, agents
  loading: false,
  error: null,
  // Cortex state
  cortex: {
    enabled: false,
    predictions: [],
    schedule: [],
    insights: [],
  },
  // Memory state
  memory: {
    stats: {},
    recentSearches: [],
    searchResults: [],
  },
  // Ghost state
  ghost: {
    enabled: false,
    suggestions: [],
    insights: [],
    stats: {},
  },
  // Agents state
  agents: {
    list: [],
    status: {},
  },
});

// ═══════════════════════════════════════════════════════════════════════════════
//  API Functions
// ═══════════════════════════════════════════════════════════════════════════════

async function fetchAllStatus() {
  try {
    const [cortex, memory, ghost, agents] = await Promise.all([
      Utils.fetch(`${API_BASE}/cortex/status`),
      Utils.fetch(`${API_BASE}/memory/status`),
      Utils.fetch(`${API_BASE}/ghost/status`),
      Utils.fetch(`${API_BASE}/agents/status`),
    ]);

    brainState.value = {
      ...brainState.value,
      cortex: {
        ...brainState.value.cortex,
        enabled: JSON.parse(cortex).learning_enabled,
        ...JSON.parse(cortex),
      },
      memory: {
        ...brainState.value.memory,
        stats: JSON.parse(memory).stats,
      },
      ghost: {
        ...brainState.value.ghost,
        enabled: JSON.parse(ghost).enabled,
        stats: JSON.parse(ghost).stats,
      },
      agents: {
        ...brainState.value.agents,
        status: JSON.parse(agents),
      },
    };
  } catch (e) {
    console.error("Brain status error:", e);
  }
}

// Cortex Functions
async function toggleCortexLearning() {
  const endpoint = brainState.value.cortex.enabled ? "stop" : "start";
  try {
    await Utils.fetch(`${API_BASE}/cortex/${endpoint}`, { method: "POST" });
    await fetchAllStatus();
  } catch (e) {
    console.error("Cortex toggle error:", e);
  }
}

async function fetchCortexPredictions() {
  try {
    const response = await Utils.fetch(`${API_BASE}/cortex/predict`);
    const data = JSON.parse(response);
    brainState.value = {
      ...brainState.value,
      cortex: {
        ...brainState.value.cortex,
        predictions: data.predictions || {},
      },
    };
  } catch (e) {
    console.error("Predictions error:", e);
  }
}

async function fetchCortexInsights() {
  try {
    const response = await Utils.fetch(`${API_BASE}/cortex/insights`);
    const data = JSON.parse(response);
    brainState.value = {
      ...brainState.value,
      cortex: {
        ...brainState.value.cortex,
        insights: data || [],
      },
    };
  } catch (e) {
    console.error("Insights error:", e);
  }
}

// Memory Functions
async function searchMemory(query) {
  if (!query.trim()) return;
  brainState.value = { ...brainState.value, loading: true };
  try {
    const response = await Utils.fetch(
      `${API_BASE}/memory/search?q=${encodeURIComponent(query)}&limit=10`
    );
    const data = JSON.parse(response);
    brainState.value = {
      ...brainState.value,
      loading: false,
      memory: {
        ...brainState.value.memory,
        searchResults: data.results || [],
      },
    };
  } catch (e) {
    brainState.value = { ...brainState.value, loading: false, error: "Search failed" };
  }
}

async function askMemory(question) {
  if (!question.trim()) return;
  brainState.value = { ...brainState.value, loading: true };
  try {
    const response = await Utils.fetch(`${API_BASE}/memory/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    return JSON.parse(response);
  } catch (e) {
    brainState.value = { ...brainState.value, loading: false, error: "Ask failed" };
    return null;
  }
}

// Ghost Functions
async function toggleGhost() {
  const endpoint = brainState.value.ghost.enabled ? "stop" : "start";
  try {
    await Utils.fetch(`${API_BASE}/ghost/${endpoint}`, { method: "POST" });
    await fetchAllStatus();
  } catch (e) {
    console.error("Ghost toggle error:", e);
  }
}

async function fetchGhostSuggestions() {
  try {
    const response = await Utils.fetch(`${API_BASE}/ghost/suggestions`);
    const data = JSON.parse(response);
    brainState.value = {
      ...brainState.value,
      ghost: {
        ...brainState.value.ghost,
        suggestions: data.suggestions || [],
      },
    };
  } catch (e) {
    console.error("Suggestions error:", e);
  }
}

async function respondToSuggestion(id, response) {
  try {
    await Utils.fetch(`${API_BASE}/ghost/suggestions/${id}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ response }),
    });
    await fetchGhostSuggestions();
  } catch (e) {
    console.error("Respond error:", e);
  }
}

// Agent Functions
async function fetchAgentsList() {
  try {
    const response = await Utils.fetch(`${API_BASE}/agents/list`);
    const data = JSON.parse(response);
    brainState.value = {
      ...brainState.value,
      agents: {
        ...brainState.value.agents,
        list: data.agents || [],
      },
    };
  } catch (e) {
    console.error("Agents list error:", e);
  }
}

async function runAgentTask(description) {
  if (!description.trim()) return;
  brainState.value = { ...brainState.value, loading: true };
  try {
    const response = await Utils.fetch(`${API_BASE}/agents/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    });
    brainState.value = { ...brainState.value, loading: false };
    return JSON.parse(response);
  } catch (e) {
    brainState.value = { ...brainState.value, loading: false, error: "Task failed" };
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  UI Components
// ═══════════════════════════════════════════════════════════════════════════════

function BrainHeader() {
  return Widget.Box({
    class_name: "brain-header",
    children: [
      Widget.Box({
        hexpand: true,
        children: [
          Widget.Label({ class_name: "brain-icon", label: "🧠" }),
          Widget.Label({ class_name: "brain-title", label: "Purma Brain" }),
        ],
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label({ label: "✕" }),
        on_clicked: () => toggleBrain(),
      }),
    ],
  });
}

function NavTabs() {
  const tabs = [
    { id: "overview", icon: "📊", label: "Overview" },
    { id: "cortex", icon: "🔮", label: "Cortex" },
    { id: "memory", icon: "💭", label: "Memory" },
    { id: "ghost", icon: "👻", label: "Ghost" },
    { id: "agents", icon: "🤖", label: "Agents" },
  ];

  return Widget.Box({
    class_name: "nav-tabs",
    children: tabs.map((tab) =>
      Widget.Button({
        class_name: brainState.bind().as((s) =>
          `nav-tab ${s.view === tab.id ? "active" : ""}`
        ),
        child: Widget.Box({
          children: [
            Widget.Label({ class_name: "tab-icon", label: tab.icon }),
            Widget.Label({ class_name: "tab-label", label: tab.label }),
          ],
        }),
        on_clicked: () => {
          brainState.value = { ...brainState.value, view: tab.id };
          if (tab.id === "cortex") fetchCortexInsights();
          if (tab.id === "ghost") fetchGhostSuggestions();
          if (tab.id === "agents") fetchAgentsList();
        },
      })
    ),
  });
}

function OverviewView() {
  return Widget.Box({
    class_name: "overview-view",
    vertical: true,
    children: [
      Widget.Label({ class_name: "view-title", label: "AI Systems Status" }),
      // Status cards
      Widget.Box({
        class_name: "status-cards",
        vertical: true,
        children: [
          // Cortex Card
          Widget.Box({
            class_name: "status-card cortex-card",
            children: [
              Widget.Label({ class_name: "card-icon", label: "🔮" }),
              Widget.Box({
                vertical: true,
                hexpand: true,
                children: [
                  Widget.Label({ class_name: "card-title", label: "Cortex", xalign: 0 }),
                  Widget.Label({
                    class_name: "card-status",
                    label: brainState.bind().as((s) =>
                      s.cortex.enabled ? "Learning..." : "Idle"
                    ),
                    xalign: 0,
                  }),
                ],
              }),
              Widget.Button({
                class_name: brainState.bind().as((s) =>
                  `toggle-btn ${s.cortex.enabled ? "active" : ""}`
                ),
                child: Widget.Label({
                  label: brainState.bind().as((s) => (s.cortex.enabled ? "ON" : "OFF")),
                }),
                on_clicked: () => toggleCortexLearning(),
              }),
            ],
          }),
          // Memory Card
          Widget.Box({
            class_name: "status-card memory-card",
            children: [
              Widget.Label({ class_name: "card-icon", label: "💭" }),
              Widget.Box({
                vertical: true,
                hexpand: true,
                children: [
                  Widget.Label({ class_name: "card-title", label: "Memory", xalign: 0 }),
                  Widget.Label({
                    class_name: "card-status",
                    label: brainState.bind().as((s) =>
                      `${s.memory.stats?.documents || 0} documents indexed`
                    ),
                    xalign: 0,
                  }),
                ],
              }),
            ],
          }),
          // Ghost Card
          Widget.Box({
            class_name: "status-card ghost-card",
            children: [
              Widget.Label({ class_name: "card-icon", label: "👻" }),
              Widget.Box({
                vertical: true,
                hexpand: true,
                children: [
                  Widget.Label({ class_name: "card-title", label: "Ghost", xalign: 0 }),
                  Widget.Label({
                    class_name: "card-status",
                    label: brainState.bind().as((s) =>
                      s.ghost.enabled ? "Observing..." : "Idle"
                    ),
                    xalign: 0,
                  }),
                ],
              }),
              Widget.Button({
                class_name: brainState.bind().as((s) =>
                  `toggle-btn ${s.ghost.enabled ? "active" : ""}`
                ),
                child: Widget.Label({
                  label: brainState.bind().as((s) => (s.ghost.enabled ? "ON" : "OFF")),
                }),
                on_clicked: () => toggleGhost(),
              }),
            ],
          }),
          // Agents Card
          Widget.Box({
            class_name: "status-card agents-card",
            children: [
              Widget.Label({ class_name: "card-icon", label: "🤖" }),
              Widget.Box({
                vertical: true,
                hexpand: true,
                children: [
                  Widget.Label({ class_name: "card-title", label: "Multi-Agent", xalign: 0 }),
                  Widget.Label({
                    class_name: "card-status",
                    label: brainState.bind().as((s) =>
                      `${Object.keys(s.agents.status?.agents || {}).length} agents ready`
                    ),
                    xalign: 0,
                  }),
                ],
              }),
            ],
          }),
        ],
      }),
    ],
  });
}

function CortexView() {
  return Widget.Box({
    class_name: "cortex-view",
    vertical: true,
    children: [
      Widget.Label({ class_name: "view-title", label: "🔮 Purma Cortex" }),
      Widget.Label({
        class_name: "view-subtitle",
        label: "Predictive AI that learns your patterns",
      }),
      // Predictions section
      Widget.Box({
        class_name: "section",
        vertical: true,
        children: [
          Widget.Label({ class_name: "section-title", label: "Predictions", xalign: 0 }),
          Widget.Button({
            class_name: "action-btn",
            child: Widget.Label({ label: "🔮 Get Predictions" }),
            on_clicked: () => fetchCortexPredictions(),
          }),
          Widget.Box({
            class_name: "predictions-list",
            vertical: true,
            children: brainState.bind().as((s) => {
              const preds = s.cortex.predictions?.next_apps || [];
              if (preds.length === 0) {
                return [
                  Widget.Label({
                    class_name: "empty-hint",
                    label: "Click to generate predictions",
                  }),
                ];
              }
              return preds.map((p) =>
                Widget.Box({
                  class_name: "prediction-item",
                  children: [
                    Widget.Label({ class_name: "pred-app", label: p.app }),
                    Widget.Label({
                      class_name: "pred-confidence",
                      label: `${Math.round(p.confidence * 100)}%`,
                    }),
                  ],
                })
              );
            }),
          }),
        ],
      }),
      // Insights section
      Widget.Box({
        class_name: "section",
        vertical: true,
        children: [
          Widget.Label({ class_name: "section-title", label: "Insights", xalign: 0 }),
          Widget.Scrollable({
            class_name: "insights-scroll",
            vexpand: true,
            child: Widget.Box({
              vertical: true,
              children: brainState.bind().as((s) => {
                const insights = s.cortex.insights || [];
                return insights.map((insight) =>
                  Widget.Box({
                    class_name: "insight-item",
                    vertical: true,
                    children: [
                      Widget.Label({
                        class_name: "insight-title",
                        label: insight.title,
                        xalign: 0,
                      }),
                      Widget.Label({
                        class_name: "insight-desc",
                        label: insight.description || "",
                        xalign: 0,
                        wrap: true,
                      }),
                    ],
                  })
                );
              }),
            }),
          }),
        ],
      }),
    ],
  });
}

function MemoryView() {
  let searchEntry;

  return Widget.Box({
    class_name: "memory-view",
    vertical: true,
    children: [
      Widget.Label({ class_name: "view-title", label: "💭 Purma Memory" }),
      Widget.Label({
        class_name: "view-subtitle",
        label: "Semantic search across all your files",
      }),
      // Search bar
      Widget.Box({
        class_name: "search-bar",
        children: [
          Widget.Entry({
            class_name: "search-entry",
            hexpand: true,
            placeholder_text: "Search your memory...",
            setup: (self) => {
              searchEntry = self;
            },
            on_accept: () => searchMemory(searchEntry.text),
          }),
          Widget.Button({
            class_name: "search-btn",
            child: Widget.Label({ label: "🔍" }),
            on_clicked: () => searchMemory(searchEntry.text),
          }),
        ],
      }),
      // Stats
      Widget.Box({
        class_name: "stats-bar",
        children: [
          Widget.Label({
            class_name: "stat",
            label: brainState.bind().as((s) =>
              `📄 ${s.memory.stats?.documents || 0} docs`
            ),
          }),
          Widget.Label({
            class_name: "stat",
            label: brainState.bind().as((s) =>
              `💾 ${s.memory.stats?.total_size_mb || 0} MB`
            ),
          }),
        ],
      }),
      // Results
      Widget.Scrollable({
        class_name: "results-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: brainState.bind().as((s) => {
            const results = s.memory.searchResults || [];
            if (results.length === 0) {
              return [
                Widget.Label({
                  class_name: "empty-hint",
                  label: "Search to find memories",
                }),
              ];
            }
            return results.map((r) =>
              Widget.Box({
                class_name: "result-item",
                children: [
                  Widget.Label({
                    class_name: "result-icon",
                    label: r.file_type === "code" ? "💻" : "📄",
                  }),
                  Widget.Box({
                    vertical: true,
                    hexpand: true,
                    children: [
                      Widget.Label({
                        class_name: "result-name",
                        label: r.filename || "Unknown",
                        xalign: 0,
                        truncate: "end",
                      }),
                      Widget.Label({
                        class_name: "result-path",
                        label: r.path || "",
                        xalign: 0,
                        truncate: "end",
                      }),
                    ],
                  }),
                  Widget.Label({
                    class_name: "result-score",
                    label: `${Math.round((r.score || 0) * 100)}%`,
                  }),
                ],
              })
            );
          }),
        }),
      }),
    ],
  });
}

function GhostView() {
  return Widget.Box({
    class_name: "ghost-view",
    vertical: true,
    children: [
      Widget.Label({ class_name: "view-title", label: "👻 Purma Ghost" }),
      Widget.Label({
        class_name: "view-subtitle",
        label: "Observes your behavior and suggests automations",
      }),
      // Stats
      Widget.Box({
        class_name: "ghost-stats",
        children: [
          Widget.Label({
            class_name: "stat",
            label: brainState.bind().as((s) =>
              `👁️ ${s.ghost.stats?.total_actions_observed || 0} actions`
            ),
          }),
          Widget.Label({
            class_name: "stat",
            label: brainState.bind().as((s) =>
              `📊 ${s.ghost.stats?.patterns_detected || 0} patterns`
            ),
          }),
          Widget.Label({
            class_name: "stat",
            label: brainState.bind().as((s) =>
              `⏱️ ${s.ghost.stats?.total_time_saved_minutes || 0}m saved`
            ),
          }),
        ],
      }),
      // Suggestions
      Widget.Label({ class_name: "section-title", label: "Suggestions", xalign: 0 }),
      Widget.Scrollable({
        class_name: "suggestions-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: brainState.bind().as((s) => {
            const suggestions = s.ghost.suggestions || [];
            if (suggestions.length === 0) {
              return [
                Widget.Label({
                  class_name: "empty-hint",
                  label: "No suggestions yet. Ghost is learning...",
                }),
              ];
            }
            return suggestions.map((sug) =>
              Widget.Box({
                class_name: "suggestion-item",
                vertical: true,
                children: [
                  Widget.Box({
                    children: [
                      Widget.Label({ class_name: "sug-icon", label: "💡" }),
                      Widget.Label({
                        class_name: "sug-title",
                        label: sug.title,
                        hexpand: true,
                        xalign: 0,
                      }),
                      Widget.Label({
                        class_name: "sug-confidence",
                        label: `${Math.round(sug.confidence * 100)}%`,
                      }),
                    ],
                  }),
                  Widget.Label({
                    class_name: "sug-desc",
                    label: sug.description,
                    xalign: 0,
                    wrap: true,
                  }),
                  Widget.Box({
                    class_name: "sug-actions",
                    children: [
                      Widget.Button({
                        class_name: "accept-btn",
                        child: Widget.Label({ label: "✓ Accept" }),
                        on_clicked: () => respondToSuggestion(sug.id, "accepted"),
                      }),
                      Widget.Button({
                        class_name: "reject-btn",
                        child: Widget.Label({ label: "✕ Reject" }),
                        on_clicked: () => respondToSuggestion(sug.id, "rejected"),
                      }),
                    ],
                  }),
                ],
              })
            );
          }),
        }),
      }),
    ],
  });
}

function AgentsView() {
  let taskEntry;

  return Widget.Box({
    class_name: "agents-view",
    vertical: true,
    children: [
      Widget.Label({ class_name: "view-title", label: "🤖 Multi-Agent System" }),
      Widget.Label({
        class_name: "view-subtitle",
        label: "Specialized AI agents working together",
      }),
      // Task input
      Widget.Box({
        class_name: "task-input",
        children: [
          Widget.Entry({
            class_name: "task-entry",
            hexpand: true,
            placeholder_text: "Describe a task for the agents...",
            setup: (self) => {
              taskEntry = self;
            },
          }),
          Widget.Button({
            class_name: "run-btn",
            child: Widget.Label({ label: "▶ Run" }),
            on_clicked: async () => {
              const result = await runAgentTask(taskEntry.text);
              if (result) {
                Utils.notify({
                  summary: "Task Complete",
                  body: "Multi-agent task finished",
                });
              }
            },
          }),
        ],
      }),
      // Agents list
      Widget.Label({ class_name: "section-title", label: "Available Agents", xalign: 0 }),
      Widget.Scrollable({
        class_name: "agents-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: brainState.bind().as((s) => {
            const agents = s.agents.list || [];
            return agents.map((agent) =>
              Widget.Box({
                class_name: "agent-item",
                children: [
                  Widget.Label({
                    class_name: "agent-icon",
                    label: agent.role === "researcher" ? "🔍" :
                           agent.role === "analyzer" ? "📊" :
                           agent.role === "executor" ? "⚡" :
                           agent.role === "coder" ? "💻" :
                           agent.role === "reviewer" ? "✅" : "🤖",
                  }),
                  Widget.Box({
                    vertical: true,
                    hexpand: true,
                    children: [
                      Widget.Label({
                        class_name: "agent-name",
                        label: agent.name,
                        xalign: 0,
                      }),
                      Widget.Label({
                        class_name: "agent-caps",
                        label: agent.capabilities?.map((c) => c.name).join(", ") || "",
                        xalign: 0,
                        truncate: "end",
                      }),
                    ],
                  }),
                ],
              })
            );
          }),
        }),
      }),
    ],
  });
}

function BrainContent() {
  return Widget.Box({
    class_name: "brain-content",
    vertical: true,
    vexpand: true,
    children: brainState.bind().as((s) => {
      switch (s.view) {
        case "cortex":
          return [CortexView()];
        case "memory":
          return [MemoryView()];
        case "ghost":
          return [GhostView()];
        case "agents":
          return [AgentsView()];
        default:
          return [OverviewView()];
      }
    }),
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Main Window
// ═══════════════════════════════════════════════════════════════════════════════

export function BrainWindow() {
  return Widget.Window({
    name: "purma-brain",
    class_name: "brain-window",
    anchor: ["top", "right"],
    exclusivity: "normal",
    layer: "overlay",
    margins: [60, 16, 16, 16],
    visible: brainState.bind().as((s) => s.visible),
    child: Widget.Box({
      class_name: "brain-popup",
      vertical: true,
      children: [BrainHeader(), NavTabs(), BrainContent()],
    }),
    setup: () => {
      fetchAllStatus();
    },
  });
}

// Bar Button
export function BrainButton() {
  return Widget.Button({
    class_name: "brain-button",
    child: Widget.Box({
      children: [
        Widget.Label({ class_name: "brain-btn-icon", label: "🧠" }),
        Widget.Label({ class_name: "brain-btn-label", label: " Brain" }),
      ],
    }),
    on_clicked: () => toggleBrain(),
    tooltip_text: "Purma Brain (Super+I)",
  });
}

// Toggle function
export function toggleBrain() {
  brainState.value = { ...brainState.value, visible: !brainState.value.visible };
  if (brainState.value.visible) {
    fetchAllStatus();
  }
}

export { brainState };
