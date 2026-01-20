/**
 * PurmaLinux - Lens Widget
 * Contextual Vision System UI
 */

const PURMA_SERVER = "http://localhost:8787";

// ============================================
// State Management
// ============================================

const LensState = Variable({
  capture: null,
  ocr: null,
  analysis: null,
  suggestions: [],
  extractedData: {},
  recentCaptures: [],
  loading: false,
  error: null,
});

const popupVisible = Variable(false);
const currentView = Variable("capture"); // capture, result, history

// ============================================
// Action Icons
// ============================================

const ACTION_ICONS = {
  copy: "",
  search: "",
  translate: "",
  explain: "",
  fix_code: "",
  run_command: "",
  open_url: "",
  save: "",
};

// ============================================
// API Functions
// ============================================

async function captureScreen(mode = "fullscreen") {
  LensState.value = { ...LensState.value, loading: true, error: null };

  try {
    const result = await Utils.execAsync([
      "curl", "-s", "-X", "POST",
      `${PURMA_SERVER}/lens/capture?mode=${mode}&do_ocr=true&do_vision=true`,
    ]);
    const data = JSON.parse(result);

    if (data.success) {
      LensState.value = {
        ...LensState.value,
        capture: data.capture,
        ocr: data.ocr,
        analysis: data.analysis,
        suggestions: data.suggestions || [],
        extractedData: data.extracted_data || {},
        loading: false,
      };
      currentView.value = "result";

      Utils.execAsync([
        "notify-send", "-i", "camera-photo",
        "Purma Lens", "Captura analizada",
      ]);
    } else {
      LensState.value = {
        ...LensState.value,
        loading: false,
        error: data.error || "Error al capturar",
      };
    }

    return data;
  } catch (e) {
    LensState.value = {
      ...LensState.value,
      loading: false,
      error: "Error de conexion",
    };
    return { error: e.message };
  }
}

async function captureRegion() {
  popupVisible.value = false;

  // Small delay to let popup close
  await new Promise((r) => setTimeout(r, 200));

  const result = await captureScreen("region");

  if (result.success) {
    popupVisible.value = true;
  }

  return result;
}

async function captureWindow() {
  return captureScreen("window");
}

async function fetchRecentCaptures() {
  try {
    const result = await Utils.execAsync([
      "curl", "-s", `${PURMA_SERVER}/lens/recent?limit=10`,
    ]);
    const data = JSON.parse(result);

    LensState.value = {
      ...LensState.value,
      recentCaptures: data.captures || [],
    };
  } catch (e) {
    console.log("Error fetching recent:", e);
  }
}

async function copyText(text) {
  await Utils.execAsync(["wl-copy", text]);
  Utils.execAsync([
    "notify-send", "-i", "edit-copy",
    "Purma Lens", "Texto copiado",
  ]);
}

async function openUrl(url) {
  await Utils.execAsync(["xdg-open", url]);
}

async function executeSuggestion(suggestion) {
  if (suggestion.action === "copy" && LensState.value.ocr?.text) {
    await copyText(LensState.value.ocr.text);
  } else if (suggestion.action === "open_url") {
    const urls = LensState.value.extractedData?.urls || [];
    if (urls.length > 0) {
      await openUrl(urls[0]);
    }
  } else if (suggestion.action === "search" && LensState.value.ocr?.text) {
    const query = encodeURIComponent(LensState.value.ocr.text.slice(0, 100));
    await Utils.execAsync(["xdg-open", `https://duckduckgo.com/?q=${query}`]);
  }
}

// ============================================
// Widget Components
// ============================================

function CapturePreview() {
  return Widget.Box({
    class_name: "capture-preview",
    vertical: true,
    vpack: "center",
    hpack: "center",
    setup: (self) => {
      self.hook(LensState, () => {
        const { capture, loading, error } = LensState.value;

        if (loading) {
          self.children = [
            Widget.Box({
              class_name: "preview-loading",
              vertical: true,
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "loading-icon spin" }),
                Widget.Label({ label: "Analizando...", class_name: "loading-text" }),
              ],
            }),
          ];
          return;
        }

        if (error) {
          self.children = [
            Widget.Box({
              class_name: "preview-error",
              vertical: true,
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "error-icon" }),
                Widget.Label({ label: error, class_name: "error-text" }),
              ],
            }),
          ];
          return;
        }

        if (!capture) {
          self.children = [
            Widget.Box({
              class_name: "preview-empty",
              vertical: true,
              spacing: 16,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({
                  label: "Captura la pantalla",
                  class_name: "empty-title",
                }),
                Widget.Label({
                  label: "Selecciona una opcion de captura",
                  class_name: "empty-hint",
                }),
              ],
            }),
          ];
          return;
        }

        // Show capture info
        self.children = [
          Widget.Box({
            class_name: "capture-info",
            vertical: true,
            spacing: 8,
            children: [
              Widget.Label({
                class_name: "capture-size",
                label: `${capture.width} x ${capture.height}`,
              }),
              Widget.Label({
                class_name: "capture-path",
                label: capture.path.split("/").pop(),
                max_width_chars: 30,
                truncate: "middle",
              }),
            ],
          }),
        ];
      });
    },
  });
}

function AnalysisPanel() {
  return Widget.Box({
    class_name: "analysis-panel",
    vertical: true,
    spacing: 8,
    setup: (self) => {
      self.hook(LensState, () => {
        const { analysis, ocr } = LensState.value;

        if (!analysis && !ocr) {
          self.visible = false;
          return;
        }

        self.visible = true;
        const children = [];

        if (analysis) {
          children.push(
            Widget.Box({
              class_name: "analysis-section",
              vertical: true,
              children: [
                Widget.Box({
                  children: [
                    Widget.Label({
                      class_name: "section-icon",
                      label: "",
                    }),
                    Widget.Label({
                      class_name: "section-title",
                      label: "Analisis",
                      hexpand: true,
                      xalign: 0,
                    }),
                    Widget.Label({
                      class_name: "content-type",
                      label: analysis.content_type || "unknown",
                    }),
                  ],
                }),
                Widget.Label({
                  class_name: "analysis-desc",
                  label: analysis.description?.slice(0, 200) || "",
                  xalign: 0,
                  wrap: true,
                }),
              ],
            })
          );

          if (analysis.error_detected) {
            children.push(
              Widget.Box({
                class_name: "error-detected",
                spacing: 8,
                children: [
                  Widget.Label({ label: "", class_name: "error-badge-icon" }),
                  Widget.Label({ label: "Error detectado", class_name: "error-badge-text" }),
                ],
              })
            );
          }
        }

        if (ocr && ocr.text) {
          children.push(
            Widget.Box({
              class_name: "ocr-section",
              vertical: true,
              children: [
                Widget.Box({
                  children: [
                    Widget.Label({
                      class_name: "section-icon",
                      label: "",
                    }),
                    Widget.Label({
                      class_name: "section-title",
                      label: "Texto extraido",
                      hexpand: true,
                      xalign: 0,
                    }),
                    Widget.Label({
                      class_name: "text-count",
                      label: `${ocr.text.length} chars`,
                    }),
                  ],
                }),
                Widget.Label({
                  class_name: "ocr-preview",
                  label: ocr.text.slice(0, 150) + (ocr.text.length > 150 ? "..." : ""),
                  xalign: 0,
                  wrap: true,
                }),
                Widget.Button({
                  class_name: "copy-text-btn",
                  child: Widget.Box({
                    spacing: 6,
                    hpack: "center",
                    children: [
                      Widget.Label(""),
                      Widget.Label("Copiar texto"),
                    ],
                  }),
                  on_clicked: () => copyText(ocr.text),
                }),
              ],
            })
          );
        }

        self.children = children;
      });
    },
  });
}

function SuggestionItem(suggestion) {
  const icon = ACTION_ICONS[suggestion.action] || "";

  return Widget.Button({
    class_name: "suggestion-item",
    on_clicked: () => executeSuggestion(suggestion),
    child: Widget.Box({
      spacing: 8,
      children: [
        Widget.Label({
          class_name: "suggestion-icon",
          label: suggestion.icon || icon,
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "suggestion-title",
              label: suggestion.title,
              xalign: 0,
            }),
            Widget.Label({
              class_name: "suggestion-desc",
              label: suggestion.description,
              xalign: 0,
              max_width_chars: 35,
              truncate: "end",
            }),
          ],
        }),
        Widget.Label({
          class_name: "suggestion-arrow",
          label: "",
        }),
      ],
    }),
  });
}

function SuggestionsPanel() {
  return Widget.Box({
    class_name: "suggestions-panel",
    vertical: true,
    spacing: 4,
    setup: (self) => {
      self.hook(LensState, () => {
        const { suggestions } = LensState.value;

        if (!suggestions || suggestions.length === 0) {
          self.visible = false;
          return;
        }

        self.visible = true;
        self.children = [
          Widget.Label({
            class_name: "panel-title",
            label: " Acciones sugeridas",
            xalign: 0,
          }),
          ...suggestions.slice(0, 5).map((s) => SuggestionItem(s)),
        ];
      });
    },
  });
}

function ExtractedDataPanel() {
  return Widget.Box({
    class_name: "extracted-panel",
    vertical: true,
    spacing: 4,
    setup: (self) => {
      self.hook(LensState, () => {
        const { extractedData } = LensState.value;

        const hasData = extractedData &&
          ((extractedData.urls && extractedData.urls.length > 0) ||
           (extractedData.emails && extractedData.emails.length > 0));

        if (!hasData) {
          self.visible = false;
          return;
        }

        self.visible = true;
        const children = [
          Widget.Label({
            class_name: "panel-title",
            label: " Datos extraidos",
            xalign: 0,
          }),
        ];

        if (extractedData.urls && extractedData.urls.length > 0) {
          children.push(
            Widget.Box({
              class_name: "data-group",
              vertical: true,
              children: [
                Widget.Label({
                  class_name: "data-label",
                  label: `URLs (${extractedData.urls.length})`,
                  xalign: 0,
                }),
                ...extractedData.urls.slice(0, 3).map((url) =>
                  Widget.Button({
                    class_name: "data-item url",
                    child: Widget.Label({
                      label: url.slice(0, 40) + (url.length > 40 ? "..." : ""),
                      xalign: 0,
                    }),
                    on_clicked: () => openUrl(url),
                  })
                ),
              ],
            })
          );
        }

        if (extractedData.emails && extractedData.emails.length > 0) {
          children.push(
            Widget.Box({
              class_name: "data-group",
              vertical: true,
              children: [
                Widget.Label({
                  class_name: "data-label",
                  label: `Emails (${extractedData.emails.length})`,
                  xalign: 0,
                }),
                ...extractedData.emails.slice(0, 3).map((email) =>
                  Widget.Button({
                    class_name: "data-item email",
                    child: Widget.Label({
                      label: email,
                      xalign: 0,
                    }),
                    on_clicked: () => copyText(email),
                  })
                ),
              ],
            })
          );
        }

        self.children = children;
      });
    },
  });
}

function CaptureButtons() {
  return Widget.Box({
    class_name: "capture-buttons",
    spacing: 8,
    homogeneous: true,
    children: [
      Widget.Button({
        class_name: "capture-btn fullscreen",
        child: Widget.Box({
          vertical: true,
          spacing: 4,
          children: [
            Widget.Label({ label: "", class_name: "btn-icon" }),
            Widget.Label({ label: "Pantalla", class_name: "btn-label" }),
          ],
        }),
        on_clicked: () => captureScreen("fullscreen"),
        tooltip_text: "Capturar pantalla completa",
      }),
      Widget.Button({
        class_name: "capture-btn region",
        child: Widget.Box({
          vertical: true,
          spacing: 4,
          children: [
            Widget.Label({ label: "", class_name: "btn-icon" }),
            Widget.Label({ label: "Region", class_name: "btn-label" }),
          ],
        }),
        on_clicked: () => captureRegion(),
        tooltip_text: "Seleccionar region",
      }),
      Widget.Button({
        class_name: "capture-btn window",
        child: Widget.Box({
          vertical: true,
          spacing: 4,
          children: [
            Widget.Label({ label: "", class_name: "btn-icon" }),
            Widget.Label({ label: "Ventana", class_name: "btn-label" }),
          ],
        }),
        on_clicked: () => captureWindow(),
        tooltip_text: "Capturar ventana activa",
      }),
    ],
  });
}

function HistoryItem(capture) {
  return Widget.Button({
    class_name: "history-item",
    child: Widget.Box({
      spacing: 8,
      children: [
        Widget.Label({
          class_name: "history-icon",
          label: capture.has_ocr ? "" : "",
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "history-type",
              label: capture.content_type || "capture",
              xalign: 0,
            }),
            Widget.Label({
              class_name: "history-preview",
              label: capture.text_preview?.slice(0, 30) || capture.path.split("/").pop(),
              xalign: 0,
              max_width_chars: 30,
              truncate: "end",
            }),
          ],
        }),
        Widget.Label({
          class_name: "history-time",
          label: formatTime(capture.timestamp),
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
      self.hook(LensState, () => {
        const { recentCaptures } = LensState.value;

        if (!recentCaptures || recentCaptures.length === 0) {
          self.children = [
            Widget.Box({
              class_name: "history-empty",
              vertical: true,
              hpack: "center",
              vpack: "center",
              spacing: 8,
              children: [
                Widget.Label({ label: "", class_name: "empty-icon" }),
                Widget.Label({ label: "Sin capturas", class_name: "empty-text" }),
              ],
            }),
          ];
          return;
        }

        self.children = recentCaptures.map((c) => HistoryItem(c));
      });
    },
  });
}

function LensHeader() {
  return Widget.Box({
    class_name: "lens-header",
    children: [
      Widget.Label({
        class_name: "lens-title",
        label: " Purma Lens",
        hexpand: true,
        xalign: 0,
      }),
      Widget.Button({
        class_name: "header-btn history-btn",
        child: Widget.Label(""),
        on_clicked: () => {
          if (currentView.value === "history") {
            currentView.value = "capture";
          } else {
            fetchRecentCaptures();
            currentView.value = "history";
          }
        },
        tooltip_text: "Historial",
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label(""),
        on_clicked: () => (popupVisible.value = false),
      }),
    ],
  });
}

function CaptureView() {
  return Widget.Box({
    vertical: true,
    spacing: 12,
    children: [
      CaptureButtons(),
      CapturePreview(),
    ],
  });
}

function ResultView() {
  return Widget.Scrollable({
    hscroll: "never",
    vscroll: "automatic",
    vexpand: true,
    child: Widget.Box({
      vertical: true,
      spacing: 12,
      children: [
        Widget.Button({
          class_name: "back-btn",
          child: Widget.Label(" Nueva captura"),
          xalign: 0,
          on_clicked: () => {
            LensState.value = {
              ...LensState.value,
              capture: null,
              ocr: null,
              analysis: null,
              suggestions: [],
            };
            currentView.value = "capture";
          },
        }),
        AnalysisPanel(),
        SuggestionsPanel(),
        ExtractedDataPanel(),
      ],
    }),
  });
}

function LensPopup() {
  return Widget.Box({
    class_name: "lens-popup",
    vertical: true,
    children: [
      LensHeader(),
      Widget.Stack({
        class_name: "lens-content",
        transition: "slide_left_right",
        shown: currentView.bind(),
        children: {
          capture: CaptureView(),
          result: ResultView(),
          history: Widget.Box({
            vertical: true,
            children: [
              Widget.Button({
                class_name: "back-btn",
                child: Widget.Label(" Volver"),
                xalign: 0,
                on_clicked: () => (currentView.value = "capture"),
              }),
              Widget.Scrollable({
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

function LensButton() {
  return Widget.Button({
    class_name: "lens-button",
    on_clicked: () => {
      popupVisible.value = !popupVisible.value;
      if (popupVisible.value) {
        currentView.value = "capture";
      }
    },
    tooltip_text: "Purma Lens - Vision Contextual",
    child: Widget.Box({
      spacing: 6,
      children: [
        Widget.Label({
          class_name: "lens-btn-icon",
          label: "",
        }),
        Widget.Label({
          class_name: "lens-btn-label",
          label: "Lens",
        }),
      ],
    }),
  });
}

// ============================================
// Main Window
// ============================================

function LensWindow() {
  return Widget.Window({
    name: "lens-popup",
    class_name: "lens-window",
    anchor: ["top", "right"],
    margins: [40, 10, 0, 0],
    visible: popupVisible.bind(),
    keymode: "on-demand",
    child: LensPopup(),
    setup: (self) => {
      self.keybind("Escape", () => (popupVisible.value = false));
    },
  });
}

// ============================================
// Toggle Functions
// ============================================

function toggleLens() {
  popupVisible.value = !popupVisible.value;
  if (popupVisible.value) {
    currentView.value = "capture";
  }
}

async function quickCapture(mode = "fullscreen") {
  await captureScreen(mode);
  popupVisible.value = true;
}

// Export
export {
  LensWindow,
  LensButton,
  toggleLens,
  quickCapture,
  captureScreen,
  captureRegion,
};
