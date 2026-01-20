/**
 * PurmaLinux - Spaces Widget
 * Contextual workspace switcher
 */

const PURMA_SERVER = "http://localhost:8787";

// ============================================
// State Management
// ============================================

const SpacesState = Variable({
  spaces: [],
  active: null,
  loading: false,
  error: null,
});

// Visible state for popup
const popupVisible = Variable(false);

// ============================================
// API Functions
// ============================================

async function fetchSpaces() {
  SpacesState.value = { ...SpacesState.value, loading: true, error: null };

  try {
    const result = await Utils.execAsync([
      "curl",
      "-s",
      `${PURMA_SERVER}/spaces`,
    ]);
    const data = JSON.parse(result);

    SpacesState.value = {
      spaces: data.spaces || [],
      active: data.active,
      loading: false,
      error: null,
    };
  } catch (e) {
    SpacesState.value = {
      ...SpacesState.value,
      loading: false,
      error: "No se pudo conectar al servidor",
    };
  }
}

async function activateSpace(spaceId) {
  SpacesState.value = { ...SpacesState.value, loading: true };

  try {
    await Utils.execAsync([
      "curl",
      "-s",
      "-X",
      "POST",
      `${PURMA_SERVER}/spaces/${spaceId}/activate`,
    ]);

    // Refresh spaces list
    await fetchSpaces();

    // Show notification
    Utils.execAsync([
      "notify-send",
      "-i",
      "workspace-switcher",
      "Purma Spaces",
      `Espacio activado`,
    ]);

    // Close popup
    popupVisible.value = false;
  } catch (e) {
    SpacesState.value = {
      ...SpacesState.value,
      loading: false,
      error: "Error al activar espacio",
    };
  }
}

async function quickSwitch(direction = "next") {
  try {
    await Utils.execAsync([
      "curl",
      "-s",
      "-X",
      "POST",
      `${PURMA_SERVER}/spaces/switch?direction=${direction}`,
    ]);
    await fetchSpaces();
  } catch (e) {
    console.error("Quick switch failed:", e);
  }
}

// ============================================
// Widget Components
// ============================================

function SpaceItem(space, isActive) {
  return Widget.Button({
    class_name: `space-item ${isActive ? "active" : ""}`,
    on_clicked: () => activateSpace(space.id),
    child: Widget.Box({
      spacing: 12,
      children: [
        Widget.Label({
          class_name: "space-icon",
          label: space.icon || "",
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "space-name",
              label: space.name || space.id,
              xalign: 0,
            }),
            Widget.Label({
              class_name: "space-desc",
              label: space.description || "",
              xalign: 0,
              max_width_chars: 30,
              truncate: "end",
            }),
          ],
        }),
        Widget.Label({
          class_name: "space-active-indicator",
          label: isActive ? "" : "",
          visible: isActive,
        }),
      ],
    }),
  });
}

function SpacesList() {
  return Widget.Box({
    class_name: "spaces-list",
    vertical: true,
    spacing: 4,
    setup: (self) => {
      self.hook(SpacesState, () => {
        const { spaces, active, loading, error } = SpacesState.value;

        if (loading) {
          self.children = [
            Widget.Box({
              class_name: "spaces-loading",
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
              class_name: "spaces-error",
              vertical: true,
              hpack: "center",
              children: [
                Widget.Label({ label: "", class_name: "error-icon" }),
                Widget.Label({ label: error, class_name: "error-text" }),
                Widget.Button({
                  label: "Reintentar",
                  class_name: "retry-btn",
                  on_clicked: () => fetchSpaces(),
                }),
              ],
            }),
          ];
          return;
        }

        if (spaces.length === 0) {
          self.children = [
            Widget.Box({
              class_name: "spaces-empty",
              vertical: true,
              hpack: "center",
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({
                  label: "No hay spaces",
                  class_name: "empty-title",
                }),
                Widget.Label({
                  label: "Usa /space-new para crear uno",
                  class_name: "empty-hint",
                }),
              ],
            }),
          ];
          return;
        }

        self.children = spaces.map((space) =>
          SpaceItem(space, space.id === active)
        );
      });
    },
  });
}

function SpacesHeader() {
  return Widget.Box({
    class_name: "spaces-header",
    children: [
      Widget.Label({
        class_name: "spaces-title",
        label: " Spaces",
        hexpand: true,
        xalign: 0,
      }),
      Widget.Button({
        class_name: "spaces-refresh",
        child: Widget.Label(""),
        on_clicked: () => fetchSpaces(),
        tooltip_text: "Actualizar",
      }),
      Widget.Button({
        class_name: "spaces-close",
        child: Widget.Label(""),
        on_clicked: () => (popupVisible.value = false),
      }),
    ],
  });
}

function QuickSwitchBar() {
  return Widget.Box({
    class_name: "quick-switch-bar",
    children: [
      Widget.Button({
        class_name: "quick-switch-btn",
        child: Widget.Label(" Anterior"),
        on_clicked: () => quickSwitch("prev"),
        hexpand: true,
      }),
      Widget.Button({
        class_name: "quick-switch-btn",
        child: Widget.Label("Siguiente "),
        on_clicked: () => quickSwitch("next"),
        hexpand: true,
      }),
    ],
  });
}

function SpacesPopup() {
  return Widget.Box({
    class_name: "spaces-popup",
    vertical: true,
    children: [
      SpacesHeader(),
      Widget.Scrollable({
        class_name: "spaces-scroll",
        hscroll: "never",
        vscroll: "automatic",
        vexpand: true,
        child: SpacesList(),
      }),
      QuickSwitchBar(),
    ],
  });
}

// ============================================
// Bar Widget (Shows current space)
// ============================================

function SpacesButton() {
  return Widget.Button({
    class_name: "spaces-button",
    on_clicked: () => {
      popupVisible.value = !popupVisible.value;
      if (popupVisible.value) {
        fetchSpaces();
      }
    },
    on_scroll_up: () => quickSwitch("prev"),
    on_scroll_down: () => quickSwitch("next"),
    tooltip_text: "Purma Spaces (scroll para cambiar)",
    child: Widget.Box({
      spacing: 6,
      children: [
        Widget.Label({
          class_name: "spaces-btn-icon",
          label: "",
        }),
        Widget.Label({
          class_name: "spaces-btn-label",
          setup: (self) => {
            self.hook(SpacesState, () => {
              const { spaces, active } = SpacesState.value;
              const activeSpace = spaces.find((s) => s.id === active);
              self.label = activeSpace
                ? `${activeSpace.icon || ""} ${activeSpace.name}`
                : "Spaces";
            });
          },
        }),
      ],
    }),
  });
}

// ============================================
// Main Window
// ============================================

function SpacesWindow() {
  return Widget.Window({
    name: "spaces-popup",
    class_name: "spaces-window",
    anchor: ["top", "right"],
    margins: [40, 10, 0, 0],
    visible: popupVisible.bind(),
    keymode: "on-demand",
    child: SpacesPopup(),
    setup: (self) => {
      self.keybind("Escape", () => (popupVisible.value = false));
    },
  });
}

// ============================================
// Toggle Function
// ============================================

function toggleSpaces() {
  popupVisible.value = !popupVisible.value;
  if (popupVisible.value) {
    fetchSpaces();
  }
}

// Initial fetch on start
Utils.timeout(2000, () => fetchSpaces());

// Export
export { SpacesWindow, SpacesButton, toggleSpaces, fetchSpaces, quickSwitch };
