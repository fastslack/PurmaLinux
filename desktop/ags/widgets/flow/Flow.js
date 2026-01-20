/**
 * PurmaLinux - Flow Widget
 * Automation by demonstration UI
 */

const PURMA_SERVER = "http://localhost:8787";

// ============================================
// State Management
// ============================================

const FlowState = Variable({
  flows: [],
  recording: false,
  recordingId: null,
  recordingName: "",
  actionCount: 0,
  runningFlows: [],
  loading: false,
  error: null,
});

const popupVisible = Variable(false);
const currentView = Variable("list"); // list, recording, detail

// ============================================
// API Functions
// ============================================

async function fetchFlows() {
  FlowState.value = { ...FlowState.value, loading: true, error: null };

  try {
    const result = await Utils.execAsync([
      "curl", "-s", `${PURMA_SERVER}/flows`,
    ]);
    const data = JSON.parse(result);

    FlowState.value = {
      ...FlowState.value,
      flows: data.flows || [],
      recording: !!data.recording,
      runningFlows: data.running || [],
      loading: false,
    };
  } catch (e) {
    FlowState.value = {
      ...FlowState.value,
      loading: false,
      error: "No se pudo conectar al servidor",
    };
  }
}

async function startRecording(name = "") {
  try {
    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      `${PURMA_SERVER}/flow/recording/start?name=${encodeURIComponent(name || "Nueva grabacion")}`,
    ]);
    const data = JSON.parse(result);

    if (data.success) {
      FlowState.value = {
        ...FlowState.value,
        recording: true,
        recordingId: data.recording.id,
        recordingName: data.recording.name,
        actionCount: 0,
      };
      currentView.value = "recording";

      Utils.execAsync([
        "notify-send", "-i", "media-record",
        "Purma Flow", "Grabacion iniciada - realiza tus acciones",
      ]);
    }

    return data;
  } catch (e) {
    return { error: e.message };
  }
}

async function stopRecording() {
  try {
    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      `${PURMA_SERVER}/flow/recording/stop`,
    ]);
    const data = JSON.parse(result);

    if (data.success) {
      FlowState.value = {
        ...FlowState.value,
        recording: false,
        recordingId: null,
      };

      // Ask to analyze
      currentView.value = "list";
      await fetchFlows();

      Utils.execAsync([
        "notify-send", "-i", "media-playback-stop",
        "Purma Flow",
        `Grabacion terminada: ${data.recording.actions_count} acciones`,
      ]);
    }

    return data;
  } catch (e) {
    return { error: e.message };
  }
}

async function runFlow(flowId) {
  try {
    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      `${PURMA_SERVER}/flows/${flowId}/run`,
    ]);
    const data = JSON.parse(result);

    if (data.success) {
      Utils.execAsync([
        "notify-send", "-i", "system-run",
        "Purma Flow",
        `Flow ejecutado: ${data.flow_name}`,
      ]);
      await fetchFlows();
    }

    return data;
  } catch (e) {
    return { error: e.message };
  }
}

async function analyzeRecording(recordingId) {
  try {
    FlowState.value = { ...FlowState.value, loading: true };

    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      `${PURMA_SERVER}/flow/recordings/${recordingId}/analyze`,
    ]);
    const data = JSON.parse(result);

    FlowState.value = { ...FlowState.value, loading: false };

    if (data.success) {
      Utils.execAsync([
        "notify-send", "-i", "emblem-ok",
        "Purma Flow",
        `Flow creado: ${data.flow.name}`,
      ]);
      await fetchFlows();
    }

    return data;
  } catch (e) {
    FlowState.value = { ...FlowState.value, loading: false };
    return { error: e.message };
  }
}

async function createFlowFromDescription(description) {
  try {
    FlowState.value = { ...FlowState.value, loading: true };

    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      "-H", "Content-Type: application/json",
      `${PURMA_SERVER}/flows?from_description=${encodeURIComponent(description)}&name=AI+Flow`,
    ]);
    const data = JSON.parse(result);

    FlowState.value = { ...FlowState.value, loading: false };

    if (data.success) {
      await fetchFlows();
    }

    return data;
  } catch (e) {
    FlowState.value = { ...FlowState.value, loading: false };
    return { error: e.message };
  }
}

// ============================================
// Widget Components
// ============================================

function FlowItem(flow) {
  const isRunning = FlowState.value.runningFlows.includes(flow.id);

  return Widget.Button({
    class_name: `flow-item ${isRunning ? "running" : ""} ${!flow.enabled ? "disabled" : ""}`,
    on_clicked: () => runFlow(flow.id),
    child: Widget.Box({
      spacing: 12,
      children: [
        Widget.Label({
          class_name: "flow-icon",
          label: flow.icon || "⚡",
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Box({
              children: [
                Widget.Label({
                  class_name: "flow-name",
                  label: flow.name,
                  xalign: 0,
                  hexpand: true,
                }),
                Widget.Label({
                  class_name: "flow-runs",
                  label: `${flow.run_count}x`,
                  visible: flow.run_count > 0,
                }),
              ],
            }),
            Widget.Label({
              class_name: "flow-desc",
              label: flow.description || `${flow.steps_count} pasos`,
              xalign: 0,
              max_width_chars: 35,
              truncate: "end",
            }),
          ],
        }),
        Widget.Box({
          vertical: true,
          children: [
            Widget.Label({
              class_name: "flow-status",
              label: isRunning ? "" : (flow.enabled ? "" : ""),
            }),
          ],
        }),
      ],
    }),
  });
}

function FlowsList() {
  return Widget.Box({
    class_name: "flows-list",
    vertical: true,
    spacing: 4,
    setup: (self) => {
      self.hook(FlowState, () => {
        const { flows, loading, error } = FlowState.value;

        if (loading) {
          self.children = [
            Widget.Box({
              class_name: "flows-loading",
              hpack: "center",
              vpack: "center",
              child: Widget.Label("Cargando..."),
            }),
          ];
          return;
        }

        if (error) {
          self.children = [
            Widget.Box({
              class_name: "flows-error",
              vertical: true,
              hpack: "center",
              children: [
                Widget.Label({ label: "", class_name: "error-icon" }),
                Widget.Label({ label: error, class_name: "error-text" }),
              ],
            }),
          ];
          return;
        }

        if (flows.length === 0) {
          self.children = [
            Widget.Box({
              class_name: "flows-empty",
              vertical: true,
              hpack: "center",
              spacing: 12,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({
                  label: "No hay flows",
                  class_name: "empty-title",
                }),
                Widget.Label({
                  label: "Graba acciones o crea con IA",
                  class_name: "empty-hint",
                }),
              ],
            }),
          ];
          return;
        }

        self.children = flows.map((flow) => FlowItem(flow));
      });
    },
  });
}

function RecordingView() {
  return Widget.Box({
    class_name: "recording-view",
    vertical: true,
    hpack: "center",
    vpack: "center",
    spacing: 16,
    children: [
      Widget.Box({
        class_name: "recording-indicator",
        child: Widget.Label({
          label: "",
          class_name: "recording-icon pulse",
        }),
      }),
      Widget.Label({
        class_name: "recording-title",
        label: "Grabando...",
      }),
      Widget.Label({
        class_name: "recording-hint",
        label: "Realiza las acciones que quieres automatizar",
      }),
      Widget.Label({
        class_name: "recording-count",
        setup: (self) => {
          self.hook(FlowState, () => {
            self.label = `${FlowState.value.actionCount} acciones`;
          });
        },
      }),
      Widget.Button({
        class_name: "stop-recording-btn",
        child: Widget.Box({
          spacing: 8,
          children: [
            Widget.Label(""),
            Widget.Label("Detener grabacion"),
          ],
        }),
        on_clicked: () => stopRecording(),
      }),
    ],
  });
}

function FlowHeader() {
  return Widget.Box({
    class_name: "flow-header",
    children: [
      Widget.Label({
        class_name: "flow-title",
        label: "⚡ Purma Flow",
        hexpand: true,
        xalign: 0,
      }),
      Widget.Button({
        class_name: "flow-refresh",
        child: Widget.Label(""),
        on_clicked: () => fetchFlows(),
        tooltip_text: "Actualizar",
      }),
      Widget.Button({
        class_name: "flow-close",
        child: Widget.Label(""),
        on_clicked: () => (popupVisible.value = false),
      }),
    ],
  });
}

function ActionBar() {
  return Widget.Box({
    class_name: "flow-actions",
    spacing: 8,
    children: [
      Widget.Button({
        class_name: "action-btn record",
        hexpand: true,
        child: Widget.Box({
          hpack: "center",
          spacing: 6,
          children: [
            Widget.Label(""),
            Widget.Label("Grabar"),
          ],
        }),
        on_clicked: () => startRecording(),
        tooltip_text: "Grabar nuevas acciones",
      }),
      Widget.Button({
        class_name: "action-btn create",
        hexpand: true,
        child: Widget.Box({
          hpack: "center",
          spacing: 6,
          children: [
            Widget.Label(""),
            Widget.Label("Crear con IA"),
          ],
        }),
        on_clicked: () => {
          // Open dialog or input for description
          Utils.execAsync([
            "zenity", "--entry",
            "--title=Purma Flow",
            "--text=Describe lo que quieres automatizar:",
            "--width=400",
          ]).then((description) => {
            if (description && description.trim()) {
              createFlowFromDescription(description.trim());
            }
          }).catch(() => {});
        },
        tooltip_text: "Crear flow con IA",
      }),
    ],
  });
}

function FlowPopup() {
  return Widget.Box({
    class_name: "flow-popup",
    vertical: true,
    children: [
      FlowHeader(),
      Widget.Stack({
        class_name: "flow-content",
        transition: "slide_left_right",
        shown: currentView.bind(),
        children: {
          list: Widget.Box({
            vertical: true,
            children: [
              Widget.Scrollable({
                class_name: "flows-scroll",
                hscroll: "never",
                vscroll: "automatic",
                vexpand: true,
                child: FlowsList(),
              }),
              ActionBar(),
            ],
          }),
          recording: RecordingView(),
        },
      }),
    ],
  });
}

// ============================================
// Bar Widget
// ============================================

function FlowButton() {
  return Widget.Button({
    class_name: "flow-button",
    on_clicked: () => {
      popupVisible.value = !popupVisible.value;
      if (popupVisible.value) {
        fetchFlows();
        currentView.value = FlowState.value.recording ? "recording" : "list";
      }
    },
    tooltip_text: "Purma Flow - Automatizacion",
    child: Widget.Box({
      spacing: 6,
      children: [
        Widget.Label({
          class_name: "flow-btn-icon",
          setup: (self) => {
            self.hook(FlowState, () => {
              self.label = FlowState.value.recording ? "" : "⚡";
              self.class_name = FlowState.value.recording
                ? "flow-btn-icon recording"
                : "flow-btn-icon";
            });
          },
        }),
        Widget.Label({
          class_name: "flow-btn-label",
          label: "Flow",
        }),
      ],
    }),
  });
}

// ============================================
// Main Window
// ============================================

function FlowWindow() {
  return Widget.Window({
    name: "flow-popup",
    class_name: "flow-window",
    anchor: ["top", "right"],
    margins: [40, 10, 0, 0],
    visible: popupVisible.bind(),
    keymode: "on-demand",
    child: FlowPopup(),
    setup: (self) => {
      self.keybind("Escape", () => (popupVisible.value = false));
    },
  });
}

// ============================================
// Toggle Function
// ============================================

function toggleFlow() {
  popupVisible.value = !popupVisible.value;
  if (popupVisible.value) {
    fetchFlows();
    currentView.value = FlowState.value.recording ? "recording" : "list";
  }
}

function toggleRecording() {
  if (FlowState.value.recording) {
    stopRecording();
  } else {
    startRecording();
  }
}

// Initial fetch on start
Utils.timeout(3000, () => fetchFlows());

// Export
export {
  FlowWindow,
  FlowButton,
  toggleFlow,
  toggleRecording,
  fetchFlows,
  startRecording,
  stopRecording,
};
