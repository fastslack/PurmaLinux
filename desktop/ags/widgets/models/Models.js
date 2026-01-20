/**
 * PurmaLinux - Models Widget
 * Author: Matías Aguirre
 * Company: Matware
 *
 * Easy management of local AI models via Ollama
 */

const API_BASE = "http://localhost:11435";

// State management
const modelsState = Variable({
  visible: false,
  view: "installed", // installed, available, packs
  loading: false,
  error: null,
  ollamaRunning: false,
  installed: [],
  available: [],
  recommended: [],
  packs: {},
  systemInfo: null,
  installing: null, // model being installed
  installProgress: 0,
});

// ═══════════════════════════════════════════════════════════════════════════════
//  API Functions
// ═══════════════════════════════════════════════════════════════════════════════

async function fetchStatus() {
  try {
    const response = await Utils.fetch(`${API_BASE}/models/status`);
    const data = JSON.parse(response);
    modelsState.value = {
      ...modelsState.value,
      ollamaRunning: data.running,
      installed: data.installed || [],
    };
  } catch (e) {
    console.error("Models status error:", e);
    modelsState.value = { ...modelsState.value, ollamaRunning: false };
  }
}

async function fetchAvailable() {
  try {
    const response = await Utils.fetch(`${API_BASE}/models/available`);
    const data = JSON.parse(response);
    modelsState.value = {
      ...modelsState.value,
      available: data.models || [],
    };
  } catch (e) {
    console.error("Available models error:", e);
  }
}

async function fetchRecommended() {
  try {
    const response = await Utils.fetch(`${API_BASE}/models/recommended`);
    const data = JSON.parse(response);
    modelsState.value = {
      ...modelsState.value,
      recommended: data.models || [],
    };
  } catch (e) {
    console.error("Recommended models error:", e);
  }
}

async function fetchPacks() {
  try {
    const response = await Utils.fetch(`${API_BASE}/models/packs`);
    const data = JSON.parse(response);
    modelsState.value = {
      ...modelsState.value,
      packs: data.packs || {},
    };
  } catch (e) {
    console.error("Packs error:", e);
  }
}

async function fetchSystemInfo() {
  try {
    const response = await Utils.fetch(`${API_BASE}/models/system-info`);
    const data = JSON.parse(response);
    modelsState.value = {
      ...modelsState.value,
      systemInfo: data,
    };
  } catch (e) {
    console.error("System info error:", e);
  }
}

async function installModel(modelId) {
  modelsState.value = {
    ...modelsState.value,
    installing: modelId,
    installProgress: 0,
  };

  try {
    const response = await Utils.fetch(`${API_BASE}/models/install/${modelId}`, {
      method: "POST",
    });
    const data = JSON.parse(response);

    if (data.success) {
      Utils.notify({
        summary: "Model Installed",
        body: `${modelId} is now ready to use`,
        iconName: "emblem-ok-symbolic",
      });
      await fetchStatus();
      await fetchAvailable();
    } else {
      Utils.notify({
        summary: "Installation Failed",
        body: data.message || "Unknown error",
        iconName: "dialog-error-symbolic",
      });
    }
  } catch (e) {
    console.error("Install error:", e);
    Utils.notify({
      summary: "Installation Failed",
      body: e.message,
      iconName: "dialog-error-symbolic",
    });
  }

  modelsState.value = { ...modelsState.value, installing: null };
}

async function removeModel(modelId) {
  try {
    const response = await Utils.fetch(`${API_BASE}/models/${modelId}`, {
      method: "DELETE",
    });
    const data = JSON.parse(response);

    if (data.success) {
      Utils.notify({
        summary: "Model Removed",
        body: `${modelId} has been deleted`,
        iconName: "user-trash-symbolic",
      });
      await fetchStatus();
      await fetchAvailable();
    }
  } catch (e) {
    console.error("Remove error:", e);
  }
}

async function installPack(packId) {
  modelsState.value = { ...modelsState.value, installing: packId };

  try {
    const response = await Utils.fetch(`${API_BASE}/models/pack/${packId}`, {
      method: "POST",
    });
    const data = JSON.parse(response);

    if (data.success) {
      Utils.notify({
        summary: "Pack Installed",
        body: `${packId} pack is ready`,
        iconName: "emblem-ok-symbolic",
      });
      await fetchStatus();
      await fetchAvailable();
    }
  } catch (e) {
    console.error("Pack install error:", e);
  }

  modelsState.value = { ...modelsState.value, installing: null };
}

// ═══════════════════════════════════════════════════════════════════════════════
//  UI Components
// ═══════════════════════════════════════════════════════════════════════════════

function ModelsHeader() {
  return Widget.Box({
    class_name: "models-header",
    children: [
      Widget.Box({
        hexpand: true,
        children: [
          Widget.Label({ class_name: "models-icon", label: "🤖" }),
          Widget.Label({ class_name: "models-title", label: "AI Models" }),
        ],
      }),
      Widget.Button({
        class_name: "header-btn refresh-btn",
        child: Widget.Label({ label: "↻" }),
        on_clicked: async () => {
          await fetchStatus();
          await fetchAvailable();
        },
        tooltip_text: "Refresh",
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label({ label: "✕" }),
        on_clicked: () => toggleModels(),
      }),
    ],
  });
}

function OllamaStatus() {
  return Widget.Box({
    class_name: modelsState.bind().as((s) =>
      `ollama-status ${s.ollamaRunning ? "running" : "stopped"}`
    ),
    children: [
      Widget.Label({
        class_name: "status-dot",
        label: modelsState.bind().as((s) => (s.ollamaRunning ? "●" : "○")),
      }),
      Widget.Label({
        class_name: "status-text",
        label: modelsState.bind().as((s) =>
          s.ollamaRunning ? "Ollama Running" : "Ollama Stopped"
        ),
      }),
      Widget.Label({
        class_name: "model-count",
        label: modelsState.bind().as((s) =>
          s.ollamaRunning ? `${s.installed.length} models` : ""
        ),
      }),
    ],
  });
}

function NavTabs() {
  const tabs = [
    { id: "installed", icon: "📦", label: "Installed" },
    { id: "available", icon: "🌐", label: "Available" },
    { id: "packs", icon: "📚", label: "Packs" },
  ];

  return Widget.Box({
    class_name: "nav-tabs",
    children: tabs.map((tab) =>
      Widget.Button({
        class_name: modelsState.bind().as((s) =>
          `nav-tab ${s.view === tab.id ? "active" : ""}`
        ),
        child: Widget.Box({
          children: [
            Widget.Label({ class_name: "tab-icon", label: tab.icon }),
            Widget.Label({ class_name: "tab-label", label: tab.label }),
          ],
        }),
        on_clicked: () => {
          modelsState.value = { ...modelsState.value, view: tab.id };
          if (tab.id === "available") fetchAvailable();
          if (tab.id === "packs") {
            fetchPacks();
            fetchSystemInfo();
          }
        },
      })
    ),
  });
}

function InstalledView() {
  return Widget.Box({
    class_name: "installed-view",
    vertical: true,
    children: [
      Widget.Scrollable({
        class_name: "models-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: modelsState.bind().as((s) => {
            if (!s.ollamaRunning) {
              return [
                Widget.Box({
                  class_name: "empty-state",
                  vertical: true,
                  children: [
                    Widget.Label({ class_name: "empty-icon", label: "⚠️" }),
                    Widget.Label({
                      class_name: "empty-text",
                      label: "Ollama is not running",
                    }),
                    Widget.Label({
                      class_name: "empty-hint",
                      label: "Run: ollama serve",
                    }),
                  ],
                }),
              ];
            }

            if (s.installed.length === 0) {
              return [
                Widget.Box({
                  class_name: "empty-state",
                  vertical: true,
                  children: [
                    Widget.Label({ class_name: "empty-icon", label: "📦" }),
                    Widget.Label({
                      class_name: "empty-text",
                      label: "No models installed",
                    }),
                    Widget.Label({
                      class_name: "empty-hint",
                      label: "Go to Available or Packs to install",
                    }),
                  ],
                }),
              ];
            }

            return s.installed.map((model) =>
              Widget.Box({
                class_name: "model-item installed",
                children: [
                  Widget.Label({
                    class_name: "model-icon",
                    label: getCategoryIcon(model.category),
                  }),
                  Widget.Box({
                    vertical: true,
                    hexpand: true,
                    children: [
                      Widget.Label({
                        class_name: "model-name",
                        label: model.name,
                        xalign: 0,
                        truncate: "end",
                      }),
                      Widget.Label({
                        class_name: "model-desc",
                        label: model.description || model.category,
                        xalign: 0,
                        truncate: "end",
                      }),
                    ],
                  }),
                  Widget.Label({
                    class_name: "model-size",
                    label: model.size_human,
                  }),
                  Widget.Button({
                    class_name: "remove-btn",
                    child: Widget.Label({ label: "🗑️" }),
                    on_clicked: () => removeModel(model.name),
                    tooltip_text: "Remove model",
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

function AvailableView() {
  return Widget.Box({
    class_name: "available-view",
    vertical: true,
    children: [
      // Category filter
      Widget.Box({
        class_name: "category-filter",
        children: [
          Widget.Label({ class_name: "filter-label", label: "Filter:" }),
          Widget.Button({
            class_name: "filter-btn active",
            child: Widget.Label({ label: "All" }),
          }),
          Widget.Button({
            class_name: "filter-btn",
            child: Widget.Label({ label: "⭐ Recommended" }),
            on_clicked: () => fetchRecommended(),
          }),
        ],
      }),
      Widget.Scrollable({
        class_name: "models-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: modelsState.bind().as((s) => {
            const models = s.available.length > 0 ? s.available : s.recommended;

            if (models.length === 0) {
              return [
                Widget.Label({
                  class_name: "empty-hint",
                  label: "Loading available models...",
                }),
              ];
            }

            return models.map((model) =>
              Widget.Box({
                class_name: `model-item ${model.installed ? "installed" : ""}`,
                children: [
                  Widget.Label({
                    class_name: "model-icon",
                    label: getCategoryIcon(model.category),
                  }),
                  Widget.Box({
                    vertical: true,
                    hexpand: true,
                    children: [
                      Widget.Box({
                        children: [
                          Widget.Label({
                            class_name: "model-name",
                            label: model.name || model.id,
                            xalign: 0,
                          }),
                          model.recommended
                            ? Widget.Label({
                                class_name: "recommended-badge",
                                label: "⭐",
                              })
                            : null,
                        ].filter(Boolean),
                      }),
                      Widget.Label({
                        class_name: "model-desc",
                        label: model.description,
                        xalign: 0,
                        truncate: "end",
                      }),
                      Widget.Box({
                        class_name: "model-meta",
                        children: [
                          Widget.Label({
                            class_name: "meta-item",
                            label: `📊 ${model.parameters}`,
                          }),
                          Widget.Label({
                            class_name: "meta-item",
                            label: `💾 ${model.size}`,
                          }),
                          Widget.Label({
                            class_name: "meta-item",
                            label: `🎮 ${model.vram}`,
                          }),
                        ],
                      }),
                    ],
                  }),
                  model.installed
                    ? Widget.Label({
                        class_name: "installed-badge",
                        label: "✓",
                      })
                    : Widget.Button({
                        class_name: modelsState.bind().as((st) =>
                          `install-btn ${st.installing === model.id ? "installing" : ""}`
                        ),
                        child: Widget.Label({
                          label: modelsState.bind().as((st) =>
                            st.installing === model.id ? "..." : "Install"
                          ),
                        }),
                        on_clicked: () => installModel(model.id),
                        sensitive: modelsState.bind().as((st) => !st.installing),
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

function PacksView() {
  return Widget.Box({
    class_name: "packs-view",
    vertical: true,
    children: [
      // System recommendation
      Widget.Box({
        class_name: "system-rec",
        vertical: true,
        visible: modelsState.bind().as((s) => s.systemInfo !== null),
        children: [
          Widget.Label({
            class_name: "rec-title",
            label: "📊 System Analysis",
            xalign: 0,
          }),
          Widget.Label({
            class_name: "rec-info",
            label: modelsState.bind().as((s) =>
              s.systemInfo
                ? `RAM: ${s.systemInfo.ram_total_gb}GB • Recommended: ${s.systemInfo.recommended_pack}`
                : ""
            ),
            xalign: 0,
          }),
        ],
      }),
      // Packs list
      Widget.Scrollable({
        class_name: "packs-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: modelsState.bind().as((s) => {
            const packs = Object.entries(s.packs);

            if (packs.length === 0) {
              return [
                Widget.Label({
                  class_name: "empty-hint",
                  label: "Loading packs...",
                }),
              ];
            }

            return packs.map(([id, pack]) =>
              Widget.Box({
                class_name: `pack-item ${
                  s.systemInfo?.recommended_pack === id ? "recommended" : ""
                }`,
                vertical: true,
                children: [
                  Widget.Box({
                    children: [
                      Widget.Label({
                        class_name: "pack-icon",
                        label: getPackIcon(id),
                      }),
                      Widget.Box({
                        vertical: true,
                        hexpand: true,
                        children: [
                          Widget.Box({
                            children: [
                              Widget.Label({
                                class_name: "pack-name",
                                label: pack.name,
                                xalign: 0,
                              }),
                              s.systemInfo?.recommended_pack === id
                                ? Widget.Label({
                                    class_name: "rec-badge",
                                    label: "Recommended",
                                  })
                                : null,
                            ].filter(Boolean),
                          }),
                          Widget.Label({
                            class_name: "pack-desc",
                            label: pack.description,
                            xalign: 0,
                          }),
                        ],
                      }),
                      Widget.Button({
                        class_name: modelsState.bind().as((st) =>
                          `install-btn ${st.installing === id ? "installing" : ""}`
                        ),
                        child: Widget.Label({
                          label: modelsState.bind().as((st) =>
                            st.installing === id ? "Installing..." : "Install"
                          ),
                        }),
                        on_clicked: () => installPack(id),
                        sensitive: modelsState.bind().as((st) => !st.installing),
                      }),
                    ],
                  }),
                  Widget.Box({
                    class_name: "pack-models",
                    children: [
                      Widget.Label({
                        class_name: "pack-models-label",
                        label: `Models: ${pack.models.join(", ")}`,
                        xalign: 0,
                        wrap: true,
                      }),
                    ],
                  }),
                  Widget.Label({
                    class_name: "pack-size",
                    label: `Total size: ${pack.total_size}`,
                    xalign: 0,
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

function ModelsContent() {
  return Widget.Box({
    class_name: "models-content",
    vertical: true,
    vexpand: true,
    children: modelsState.bind().as((s) => {
      switch (s.view) {
        case "available":
          return [AvailableView()];
        case "packs":
          return [PacksView()];
        default:
          return [InstalledView()];
      }
    }),
  });
}

// Helper functions
function getCategoryIcon(category) {
  const icons = {
    general: "💬",
    coding: "💻",
    vision: "👁️",
    embedding: "🔗",
    chat: "💭",
    uncensored: "🔓",
    tiny: "🐜",
  };
  return icons[category] || "🤖";
}

function getPackIcon(packId) {
  const icons = {
    minimal: "🪶",
    standard: "📦",
    developer: "💻",
    creative: "🎨",
    poweruser: "🚀",
  };
  return icons[packId] || "📚";
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Main Window
// ═══════════════════════════════════════════════════════════════════════════════

export function ModelsWindow() {
  return Widget.Window({
    name: "purma-models",
    class_name: "models-window",
    anchor: ["top", "right"],
    exclusivity: "normal",
    layer: "overlay",
    margins: [60, 16, 16, 16],
    visible: modelsState.bind().as((s) => s.visible),
    child: Widget.Box({
      class_name: "models-popup",
      vertical: true,
      children: [ModelsHeader(), OllamaStatus(), NavTabs(), ModelsContent()],
    }),
    setup: () => {
      fetchStatus();
      fetchRecommended();
    },
  });
}

// Bar Button
export function ModelsButton() {
  return Widget.Button({
    class_name: modelsState.bind().as((s) =>
      `models-button ${s.ollamaRunning ? "running" : "stopped"}`
    ),
    child: Widget.Box({
      children: [
        Widget.Label({ class_name: "models-btn-icon", label: "🤖" }),
        Widget.Label({
          class_name: "models-btn-label",
          label: modelsState.bind().as((s) =>
            s.ollamaRunning ? ` ${s.installed.length}` : ""
          ),
        }),
      ],
    }),
    on_clicked: () => toggleModels(),
    tooltip_text: "AI Models (Ollama)",
  });
}

// Toggle function
export function toggleModels() {
  modelsState.value = { ...modelsState.value, visible: !modelsState.value.visible };
  if (modelsState.value.visible) {
    fetchStatus();
  }
}

export { modelsState };
