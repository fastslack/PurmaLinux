/**
 * PurmaLinux - Scribe Widget
 * AI-Powered Voice Assistant
 */

const API_BASE = "http://localhost:11435";

// State management
const scribeState = Variable({
  visible: false,
  view: "main", // main, recording, transcription, history, speak
  isRecording: false,
  recordingId: null,
  recordingDuration: 0,
  transcription: null,
  history: [],
  voices: [],
  selectedVoice: null,
  speakText: "",
  loading: false,
  error: null,
});

// Recording timer
let recordingTimer = null;

// API Functions
async function fetchScribeStatus() {
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/status`);
    const data = JSON.parse(response);
    scribeState.value = {
      ...scribeState.value,
      isRecording: data.is_recording,
      recordingId: data.current_recording_id,
    };
  } catch (e) {
    console.error("Scribe status error:", e);
  }
}

async function fetchVoices() {
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/voices`);
    const data = JSON.parse(response);
    scribeState.value = {
      ...scribeState.value,
      voices: data.voices || [],
      selectedVoice: data.voices?.[0]?.id || null,
    };
  } catch (e) {
    console.error("Fetch voices error:", e);
  }
}

async function fetchHistory() {
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/history?limit=20`);
    const data = JSON.parse(response);
    scribeState.value = { ...scribeState.value, history: data.transcriptions || [] };
  } catch (e) {
    console.error("Fetch history error:", e);
  }
}

async function startRecording() {
  scribeState.value = { ...scribeState.value, loading: true, error: null };
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/record/start`, {
      method: "POST",
    });
    const data = JSON.parse(response);
    if (data.success) {
      scribeState.value = {
        ...scribeState.value,
        isRecording: true,
        recordingId: data.recording_id,
        recordingDuration: 0,
        view: "recording",
        loading: false,
      };
      // Start duration timer
      recordingTimer = setInterval(() => {
        scribeState.value = {
          ...scribeState.value,
          recordingDuration: scribeState.value.recordingDuration + 1,
        };
      }, 1000);
    }
  } catch (e) {
    scribeState.value = { ...scribeState.value, error: "Failed to start recording", loading: false };
  }
}

async function stopRecording() {
  if (recordingTimer) {
    clearInterval(recordingTimer);
    recordingTimer = null;
  }
  scribeState.value = { ...scribeState.value, loading: true };
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/record/stop`, {
      method: "POST",
    });
    const data = JSON.parse(response);
    if (data.success) {
      scribeState.value = {
        ...scribeState.value,
        isRecording: false,
        loading: false,
      };
      // Auto-transcribe
      await transcribeRecording(data.recording_id);
    }
  } catch (e) {
    scribeState.value = { ...scribeState.value, error: "Failed to stop recording", loading: false };
  }
}

async function transcribeRecording(recordingId) {
  scribeState.value = { ...scribeState.value, loading: true, view: "transcription" };
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/transcribe/${recordingId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summarize: true }),
    });
    const data = JSON.parse(response);
    scribeState.value = {
      ...scribeState.value,
      transcription: data,
      loading: false,
    };
    await fetchHistory();
  } catch (e) {
    scribeState.value = { ...scribeState.value, error: "Transcription failed", loading: false };
  }
}

async function quickRecord(seconds = 5) {
  scribeState.value = { ...scribeState.value, loading: true, view: "transcription" };
  try {
    const response = await Utils.fetch(`${API_BASE}/scribe/quick?duration=${seconds}`, {
      method: "POST",
    });
    const data = JSON.parse(response);
    scribeState.value = {
      ...scribeState.value,
      transcription: data,
      loading: false,
    };
    await fetchHistory();
  } catch (e) {
    scribeState.value = { ...scribeState.value, error: "Quick record failed", loading: false };
  }
}

async function speakText(text) {
  if (!text.trim()) return;
  scribeState.value = { ...scribeState.value, loading: true };
  try {
    await Utils.fetch(`${API_BASE}/scribe/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        voice: scribeState.value.selectedVoice,
      }),
    });
    scribeState.value = { ...scribeState.value, loading: false };
  } catch (e) {
    scribeState.value = { ...scribeState.value, error: "Speech failed", loading: false };
  }
}

async function copyToClipboard(text) {
  await Utils.execAsync(["wl-copy", text]);
}

// Utility
function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// UI Components
function ScribeHeader() {
  return Widget.Box({
    class_name: "scribe-header",
    children: [
      Widget.Box({
        hexpand: true,
        children: [
          Widget.Label({ class_name: "scribe-icon", label: "🎙️" }),
          Widget.Label({ class_name: "scribe-title", label: "Purma Scribe" }),
        ],
      }),
      Widget.Button({
        class_name: "header-btn history-btn",
        child: Widget.Label({ label: "📜" }),
        on_clicked: () => {
          scribeState.value = { ...scribeState.value, view: "history" };
          fetchHistory();
        },
        tooltip_text: "History",
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label({ label: "✕" }),
        on_clicked: () => toggleScribe(),
      }),
    ],
  });
}

function MainView() {
  return Widget.Box({
    class_name: "main-view",
    vertical: true,
    vexpand: true,
    vpack: "center",
    children: [
      Widget.Label({ class_name: "main-icon", label: "🎙️" }),
      Widget.Label({ class_name: "main-title", label: "Voice Assistant" }),
      Widget.Label({ class_name: "main-hint", label: "Record, transcribe, and speak with AI" }),
      Widget.Box({
        class_name: "action-buttons",
        homogeneous: true,
        children: [
          Widget.Button({
            class_name: "action-btn record-btn",
            child: Widget.Box({
              vertical: true,
              children: [
                Widget.Label({ class_name: "action-icon", label: "⏺️" }),
                Widget.Label({ class_name: "action-label", label: "Record" }),
              ],
            }),
            on_clicked: () => startRecording(),
            tooltip_text: "Start Recording",
          }),
          Widget.Button({
            class_name: "action-btn quick-btn",
            child: Widget.Box({
              vertical: true,
              children: [
                Widget.Label({ class_name: "action-icon", label: "⚡" }),
                Widget.Label({ class_name: "action-label", label: "Quick (5s)" }),
              ],
            }),
            on_clicked: () => quickRecord(5),
            tooltip_text: "Quick 5 Second Recording",
          }),
          Widget.Button({
            class_name: "action-btn speak-btn",
            child: Widget.Box({
              vertical: true,
              children: [
                Widget.Label({ class_name: "action-icon", label: "🔊" }),
                Widget.Label({ class_name: "action-label", label: "Speak" }),
              ],
            }),
            on_clicked: () => {
              scribeState.value = { ...scribeState.value, view: "speak" };
              fetchVoices();
            },
            tooltip_text: "Text to Speech",
          }),
        ],
      }),
    ],
  });
}

function RecordingView() {
  return Widget.Box({
    class_name: "recording-view",
    vertical: true,
    vexpand: true,
    vpack: "center",
    children: [
      Widget.Box({
        class_name: "recording-indicator",
        children: [
          Widget.Label({ class_name: "recording-dot", label: "●" }),
          Widget.Label({ class_name: "recording-text", label: "Recording..." }),
        ],
      }),
      Widget.Label({
        class_name: "recording-duration",
        label: scribeState.bind().as((s) => formatDuration(s.recordingDuration)),
      }),
      Widget.Box({
        class_name: "waveform",
        children: [
          Widget.Label({ class_name: "wave-bar", label: "▁" }),
          Widget.Label({ class_name: "wave-bar", label: "▃" }),
          Widget.Label({ class_name: "wave-bar", label: "▅" }),
          Widget.Label({ class_name: "wave-bar", label: "▇" }),
          Widget.Label({ class_name: "wave-bar", label: "▅" }),
          Widget.Label({ class_name: "wave-bar", label: "▃" }),
          Widget.Label({ class_name: "wave-bar", label: "▁" }),
        ],
      }),
      Widget.Button({
        class_name: "stop-btn",
        child: Widget.Label({ label: "⏹️ Stop & Transcribe" }),
        on_clicked: () => stopRecording(),
      }),
      Widget.Button({
        class_name: "cancel-btn",
        child: Widget.Label({ label: "Cancel" }),
        on_clicked: () => {
          if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
          }
          scribeState.value = { ...scribeState.value, isRecording: false, view: "main" };
        },
      }),
    ],
  });
}

function TranscriptionView() {
  return Widget.Box({
    class_name: "transcription-view",
    vertical: true,
    children: [
      Widget.Button({
        class_name: "back-btn",
        child: Widget.Label({ label: "← Back" }),
        on_clicked: () => {
          scribeState.value = { ...scribeState.value, view: "main", transcription: null };
        },
      }),
      Widget.Label({ class_name: "view-title", label: "📝 Transcription" }),
      Widget.Box({
        class_name: "transcription-content",
        vertical: true,
        visible: scribeState.bind().as((s) => !s.loading && s.transcription),
        children: [
          Widget.Scrollable({
            class_name: "transcription-scroll",
            vexpand: true,
            child: Widget.Label({
              class_name: "transcription-text",
              label: scribeState.bind().as((s) => s.transcription?.text || ""),
              wrap: true,
              xalign: 0,
              selectable: true,
            }),
          }),
          Widget.Box({
            class_name: "transcription-meta",
            visible: scribeState.bind().as((s) => !!s.transcription?.summary),
            vertical: true,
            children: [
              Widget.Label({ class_name: "meta-label", label: "AI Summary", xalign: 0 }),
              Widget.Label({
                class_name: "summary-text",
                label: scribeState.bind().as((s) => s.transcription?.summary || ""),
                wrap: true,
                xalign: 0,
              }),
            ],
          }),
          Widget.Box({
            class_name: "transcription-actions",
            children: [
              Widget.Button({
                class_name: "action-small-btn copy-btn",
                child: Widget.Label({ label: "📋 Copy" }),
                on_clicked: () => copyToClipboard(scribeState.value.transcription?.text || ""),
              }),
              Widget.Button({
                class_name: "action-small-btn speak-result-btn",
                child: Widget.Label({ label: "🔊 Speak" }),
                on_clicked: () => speakText(scribeState.value.transcription?.text || ""),
              }),
            ],
          }),
        ],
      }),
      Widget.Box({
        class_name: "loading-box",
        vertical: true,
        vexpand: true,
        vpack: "center",
        visible: scribeState.bind().as((s) => s.loading),
        children: [
          Widget.Label({ class_name: "loading-icon", label: "⏳" }),
          Widget.Label({ class_name: "loading-text", label: "Transcribing with AI..." }),
        ],
      }),
    ],
  });
}

function HistoryView() {
  return Widget.Box({
    class_name: "history-view",
    vertical: true,
    children: [
      Widget.Button({
        class_name: "back-btn",
        child: Widget.Label({ label: "← Back" }),
        on_clicked: () => {
          scribeState.value = { ...scribeState.value, view: "main" };
        },
      }),
      Widget.Label({ class_name: "view-title", label: "📜 History" }),
      Widget.Scrollable({
        class_name: "history-scroll",
        vexpand: true,
        child: Widget.Box({
          vertical: true,
          children: scribeState.bind().as((s) => {
            if (s.history.length === 0) {
              return [
                Widget.Box({
                  class_name: "empty-state",
                  vertical: true,
                  vexpand: true,
                  vpack: "center",
                  children: [
                    Widget.Label({ class_name: "empty-icon", label: "📜" }),
                    Widget.Label({ class_name: "empty-title", label: "No transcriptions yet" }),
                    Widget.Label({ class_name: "empty-hint", label: "Start recording to see history" }),
                  ],
                }),
              ];
            }
            return s.history.map((item) =>
              Widget.Button({
                class_name: "history-item",
                on_clicked: () => {
                  scribeState.value = {
                    ...scribeState.value,
                    transcription: item,
                    view: "transcription",
                  };
                },
                child: Widget.Box({
                  children: [
                    Widget.Label({ class_name: "history-icon", label: "🎤" }),
                    Widget.Box({
                      vertical: true,
                      hexpand: true,
                      children: [
                        Widget.Label({
                          class_name: "history-text",
                          label: (item.text || "").substring(0, 50) + (item.text?.length > 50 ? "..." : ""),
                          xalign: 0,
                          truncate: "end",
                        }),
                        Widget.Label({
                          class_name: "history-date",
                          label: formatDate(item.created_at),
                          xalign: 0,
                        }),
                      ],
                    }),
                    Widget.Label({ class_name: "history-arrow", label: "→" }),
                  ],
                }),
              })
            );
          }),
        }),
      }),
    ],
  });
}

function SpeakView() {
  let textEntry;

  return Widget.Box({
    class_name: "speak-view",
    vertical: true,
    children: [
      Widget.Button({
        class_name: "back-btn",
        child: Widget.Label({ label: "← Back" }),
        on_clicked: () => {
          scribeState.value = { ...scribeState.value, view: "main", speakText: "" };
        },
      }),
      Widget.Label({ class_name: "view-title", label: "🔊 Text to Speech" }),
      Widget.Box({
        class_name: "voice-selector",
        visible: scribeState.bind().as((s) => s.voices.length > 1),
        children: [
          Widget.Label({ class_name: "voice-label", label: "Voice:" }),
          Widget.Box({
            class_name: "voice-options",
            children: scribeState.bind().as((s) =>
              s.voices.slice(0, 3).map((voice) =>
                Widget.Button({
                  class_name: `voice-btn ${s.selectedVoice === voice.id ? "selected" : ""}`,
                  child: Widget.Label({ label: voice.name || voice.id }),
                  on_clicked: () => {
                    scribeState.value = { ...scribeState.value, selectedVoice: voice.id };
                  },
                })
              )
            ),
          }),
        ],
      }),
      Widget.Box({
        class_name: "speak-input",
        vertical: true,
        vexpand: true,
        children: [
          Widget.Label({ class_name: "input-label", label: "Enter text to speak:", xalign: 0 }),
          Widget.Scrollable({
            class_name: "text-scroll",
            vexpand: true,
            child: Widget.Entry({
              class_name: "speak-entry",
              placeholder_text: "Type or paste text here...",
              setup: (self) => {
                textEntry = self;
              },
            }),
          }),
        ],
      }),
      Widget.Button({
        class_name: "speak-action-btn",
        child: Widget.Label({
          label: scribeState.bind().as((s) => (s.loading ? "Speaking..." : "🔊 Speak")),
        }),
        on_clicked: () => {
          if (textEntry) {
            speakText(textEntry.text);
          }
        },
      }),
    ],
  });
}

function ScribeContent() {
  return Widget.Box({
    class_name: "scribe-content",
    vertical: true,
    vexpand: true,
    children: scribeState.bind().as((s) => {
      if (s.loading && s.view === "main") {
        return [
          Widget.Box({
            class_name: "loading-box",
            vertical: true,
            vexpand: true,
            vpack: "center",
            children: [
              Widget.Label({ class_name: "loading-icon", label: "⏳" }),
              Widget.Label({ class_name: "loading-text", label: "Processing..." }),
            ],
          }),
        ];
      }

      switch (s.view) {
        case "recording":
          return [RecordingView()];
        case "transcription":
          return [TranscriptionView()];
        case "history":
          return [HistoryView()];
        case "speak":
          return [SpeakView()];
        default:
          return [MainView()];
      }
    }),
  });
}

// Error display
function ErrorBanner() {
  return Widget.Box({
    class_name: "error-banner",
    visible: scribeState.bind().as((s) => !!s.error),
    children: [
      Widget.Label({
        class_name: "error-text",
        label: scribeState.bind().as((s) => s.error || ""),
        hexpand: true,
      }),
      Widget.Button({
        class_name: "error-dismiss",
        child: Widget.Label({ label: "✕" }),
        on_clicked: () => {
          scribeState.value = { ...scribeState.value, error: null };
        },
      }),
    ],
  });
}

// Main Window
export function ScribeWindow() {
  return Widget.Window({
    name: "purma-scribe",
    class_name: "scribe-window",
    anchor: ["top", "right"],
    exclusivity: "normal",
    layer: "overlay",
    margins: [60, 16, 16, 16],
    visible: scribeState.bind().as((s) => s.visible),
    child: Widget.Box({
      class_name: "scribe-popup",
      vertical: true,
      children: [ScribeHeader(), ErrorBanner(), ScribeContent()],
    }),
    setup: () => {
      fetchScribeStatus();
      fetchVoices();
    },
  });
}

// Bar Button
export function ScribeButton() {
  return Widget.Button({
    class_name: "scribe-button",
    child: Widget.Box({
      children: [
        Widget.Label({ class_name: "scribe-btn-icon", label: "🎙️" }),
        Widget.Label({ class_name: "scribe-btn-label", label: " Scribe" }),
      ],
    }),
    on_clicked: () => toggleScribe(),
    tooltip_text: "Purma Scribe (Super+R)",
  });
}

// Toggle function
export function toggleScribe() {
  scribeState.value = { ...scribeState.value, visible: !scribeState.value.visible };
  if (scribeState.value.visible) {
    fetchScribeStatus();
  }
}

export { scribeState };
