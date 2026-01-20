/**
 * PurmaLinux - AI Chat Widget v3.0
 * Multi-tab chat with agents, commands, and OpenCode-style interface
 */

const { Gtk, Gdk, GLib, Pango } = imports.gi;

// ============================================
// State Management
// ============================================

const generateId = () => Math.random().toString(36).substring(2, 9);

const createChat = (name = null) => ({
  id: generateId(),
  name: name || `Chat ${Date.now()}`,
  messages: [],
  agent: "purma",
  createdAt: Date.now(),
});

// Global state
const chatState = Variable({
  chats: [createChat("Principal")],
  activeTabId: null,
  isLoading: false,
  isVisible: false,
  serverStatus: "disconnected",
  agents: [],
  commands: [],
  showCommandPalette: false,
  showAgentSelector: false,
  commandFilter: "",
});

chatState.value.activeTabId = chatState.value.chats[0].id;

const PURMA_SERVER = "http://127.0.0.1:11435";

// ============================================
// State Helpers
// ============================================

function getActiveChat() {
  const state = chatState.value;
  return state.chats.find((c) => c.id === state.activeTabId) || state.chats[0];
}

function updateActiveChat(updates) {
  const state = chatState.value;
  const chatIndex = state.chats.findIndex((c) => c.id === state.activeTabId);
  if (chatIndex >= 0) {
    state.chats[chatIndex] = { ...state.chats[chatIndex], ...updates };
    chatState.setValue({ ...state });
  }
}

function addNewChat(name = null, agent = "purma") {
  const state = chatState.value;
  const newChat = createChat(name || `Chat ${state.chats.length + 1}`);
  newChat.agent = agent;
  chatState.setValue({
    ...state,
    chats: [...state.chats, newChat],
    activeTabId: newChat.id,
  });
}

function closeChat(chatId) {
  const state = chatState.value;
  if (state.chats.length <= 1) return;

  const newChats = state.chats.filter((c) => c.id !== chatId);
  const newActiveId =
    state.activeTabId === chatId ? newChats[newChats.length - 1].id : state.activeTabId;

  chatState.setValue({
    ...state,
    chats: newChats,
    activeTabId: newActiveId,
  });
}

function switchTab(chatId) {
  chatState.setValue({
    ...chatState.value,
    activeTabId: chatId,
  });
}

function setActiveAgent(agentName) {
  updateActiveChat({ agent: agentName });
  chatState.setValue({
    ...chatState.value,
    showAgentSelector: false,
  });
}

function toggleCommandPalette(show = null) {
  chatState.setValue({
    ...chatState.value,
    showCommandPalette: show !== null ? show : !chatState.value.showCommandPalette,
    showAgentSelector: false,
    commandFilter: "",
  });
}

function toggleAgentSelector(show = null) {
  chatState.setValue({
    ...chatState.value,
    showAgentSelector: show !== null ? show : !chatState.value.showAgentSelector,
    showCommandPalette: false,
  });
}

// ============================================
// API Functions
// ============================================

async function checkServerStatus() {
  try {
    const response = await Utils.fetch(`${PURMA_SERVER}/status`);
    const data = JSON.parse(response);
    chatState.setValue({
      ...chatState.value,
      serverStatus: data.ollama_connected ? "connected" : "ollama_down",
    });
  } catch {
    chatState.setValue({
      ...chatState.value,
      serverStatus: "disconnected",
    });
  }
}

async function loadAgentsAndCommands() {
  try {
    const [agentsRes, commandsRes] = await Promise.all([
      Utils.fetch(`${PURMA_SERVER}/agents`),
      Utils.fetch(`${PURMA_SERVER}/commands`),
    ]);

    const agents = JSON.parse(agentsRes).agents || [];
    const commands = JSON.parse(commandsRes).commands || [];

    chatState.setValue({
      ...chatState.value,
      agents,
      commands,
    });
  } catch (e) {
    console.error("Error loading agents/commands:", e);
  }
}

async function sendMessage(content) {
  const activeChat = getActiveChat();

  const userMessage = {
    id: generateId(),
    role: "user",
    content,
    timestamp: Date.now(),
  };

  updateActiveChat({
    messages: [...activeChat.messages, userMessage],
  });

  chatState.setValue({
    ...chatState.value,
    isLoading: true,
    showCommandPalette: false,
    showAgentSelector: false,
  });

  try {
    const response = await Utils.fetch(`${PURMA_SERVER}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: content,
        agent: activeChat.agent,
        history: activeChat.messages.slice(-10).map((m) => ({
          role: m.role,
          content: m.content,
        })),
      }),
    });

    const data = JSON.parse(response);

    const assistantMessage = {
      id: generateId(),
      role: "assistant",
      content: data.response,
      timestamp: Date.now(),
      actions: data.actions || [],
      model: data.model,
      agent: data.agent,
    };

    const currentChat = getActiveChat();
    updateActiveChat({
      messages: [...currentChat.messages, assistantMessage],
    });
  } catch (error) {
    const errorMessage = {
      id: generateId(),
      role: "error",
      content: `Error: ${error.message}`,
      timestamp: Date.now(),
    };

    const currentChat = getActiveChat();
    updateActiveChat({
      messages: [...currentChat.messages, errorMessage],
    });
  } finally {
    chatState.setValue({
      ...chatState.value,
      isLoading: false,
    });
  }
}

function clearActiveChat() {
  updateActiveChat({ messages: [] });
}

function toggleChat() {
  const newVisible = !chatState.value.isVisible;
  chatState.setValue({
    ...chatState.value,
    isVisible: newVisible,
  });

  if (newVisible) {
    checkServerStatus();
    loadAgentsAndCommands();
  }
}

// ============================================
// UI Components - Header
// ============================================

function StatusIndicator() {
  const statusText = {
    connected: "Online",
    ollama_down: "Ollama offline",
    disconnected: "Offline",
  };

  return Widget.Box({
    class_name: "status-indicator",
    children: [
      Widget.Box({
        class_name: chatState.bind().as((s) => `status-dot ${s.serverStatus}`),
      }),
      Widget.Label({
        class_name: "status-text",
        label: chatState.bind().as((s) => statusText[s.serverStatus] || "Unknown"),
      }),
    ],
  });
}

function HeaderButtons() {
  return Widget.Box({
    class_name: "header-buttons",
    spacing: 4,
    children: [
      Widget.Button({
        class_name: "header-btn",
        child: Widget.Label(""),
        tooltip_text: "Comandos",
        on_clicked: () => toggleCommandPalette(),
      }),
      Widget.Button({
        class_name: "header-btn",
        child: Widget.Label(""),
        tooltip_text: "Nuevo chat",
        on_clicked: () => addNewChat(),
      }),
      Widget.Button({
        class_name: "header-btn",
        child: Widget.Label(""),
        tooltip_text: "Limpiar chat actual",
        on_clicked: clearActiveChat,
      }),
      Widget.Button({
        class_name: "header-btn minimize",
        child: Widget.Label(""),
        tooltip_text: "Minimizar",
        on_clicked: toggleChat,
      }),
    ],
  });
}

function ChatHeader() {
  return Widget.Box({
    class_name: "chat-header",
    children: [
      Widget.Box({
        hexpand: true,
        spacing: 8,
        children: [
          Widget.Label({
            class_name: "header-logo",
            label: "󰚩",
          }),
          Widget.Label({
            class_name: "header-title",
            label: "Purma",
          }),
          StatusIndicator(),
        ],
      }),
      HeaderButtons(),
    ],
  });
}

// ============================================
// UI Components - Tabs
// ============================================

function Tab(chat, isActive) {
  const agent = chatState.value.agents.find((a) => a.name === chat.agent);
  const agentIcon = agent?.icon || "󰚩";

  const closeBtn = Widget.Button({
    class_name: "tab-close",
    child: Widget.Label("×"),
    on_clicked: (self) => {
      closeChat(chat.id);
      return true;
    },
  });

  return Widget.Button({
    class_name: `tab ${isActive ? "active" : ""}`,
    on_clicked: () => switchTab(chat.id),
    child: Widget.Box({
      spacing: 6,
      children: [
        Widget.Label({
          class_name: "tab-icon",
          label: agentIcon,
        }),
        Widget.Label({
          class_name: "tab-name",
          label: chat.name,
          max_width_chars: 12,
          truncate: "end",
        }),
        closeBtn,
      ],
    }),
  });
}

function TabBar() {
  return Widget.Box({
    class_name: "tab-bar",
    children: [
      Widget.Box({
        class_name: "tabs-container",
        hexpand: true,
        children: chatState.bind().as((state) =>
          state.chats.map((chat) => Tab(chat, chat.id === state.activeTabId))
        ),
      }),
      Widget.Button({
        class_name: "tab-add",
        child: Widget.Label("+"),
        tooltip_text: "Nuevo chat",
        on_clicked: () => addNewChat(),
      }),
    ],
  });
}

// ============================================
// UI Components - Command Palette
// ============================================

function CommandItem(cmd, onSelect) {
  return Widget.Button({
    class_name: "command-item",
    on_clicked: () => onSelect(cmd),
    child: Widget.Box({
      spacing: 12,
      children: [
        Widget.Label({
          class_name: "command-icon",
          label: cmd.icon || "",
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "command-name",
              label: `/${cmd.name}`,
              xalign: 0,
            }),
            Widget.Label({
              class_name: "command-desc",
              label: cmd.description,
              xalign: 0,
              truncate: "end",
            }),
          ],
        }),
        cmd.agent
          ? Widget.Label({
              class_name: "command-agent",
              label: `@${cmd.agent}`,
            })
          : null,
      ].filter(Boolean),
    }),
  });
}

function CommandPalette() {
  return Widget.Revealer({
    transition: "slide_down",
    transition_duration: 150,
    reveal_child: chatState.bind().as((s) => s.showCommandPalette),
    child: Widget.Box({
      class_name: "command-palette",
      vertical: true,
      children: [
        Widget.Box({
          class_name: "palette-header",
          children: [
            Widget.Label({
              class_name: "palette-title",
              label: " Comandos Rápidos",
              hexpand: true,
              xalign: 0,
            }),
            Widget.Button({
              class_name: "palette-close",
              child: Widget.Label("×"),
              on_clicked: () => toggleCommandPalette(false),
            }),
          ],
        }),
        Widget.Scrollable({
          class_name: "palette-list",
          hscroll: "never",
          vscroll: "automatic",
          child: Widget.Box({
            vertical: true,
            spacing: 4,
            children: chatState.bind().as((state) =>
              state.commands.map((cmd) =>
                CommandItem(cmd, (c) => {
                  const args = c.args?.length
                    ? c.args.map((a) => a.default || `<${a.name}>`).join(" ")
                    : "";
                  sendMessage(`/${c.name} ${args}`.trim());
                })
              )
            ),
          }),
        }),
      ],
    }),
  });
}

// ============================================
// UI Components - Agent Selector
// ============================================

function AgentItem(agent, isActive, onSelect) {
  return Widget.Button({
    class_name: `agent-item ${isActive ? "active" : ""}`,
    on_clicked: () => onSelect(agent.name),
    child: Widget.Box({
      spacing: 12,
      children: [
        Widget.Label({
          class_name: "agent-icon",
          label: agent.icon || "󰚩",
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
              class_name: "agent-desc",
              label: agent.description,
              xalign: 0,
              truncate: "end",
            }),
          ],
        }),
        Widget.Label({
          class_name: "agent-mode",
          label: agent.mode === "primary" ? "󰓾" : "",
        }),
      ],
    }),
  });
}

function AgentSelector() {
  return Widget.Revealer({
    transition: "slide_down",
    transition_duration: 150,
    reveal_child: chatState.bind().as((s) => s.showAgentSelector),
    child: Widget.Box({
      class_name: "agent-selector",
      vertical: true,
      children: [
        Widget.Box({
          class_name: "palette-header",
          children: [
            Widget.Label({
              class_name: "palette-title",
              label: "󰚩 Seleccionar Agente",
              hexpand: true,
              xalign: 0,
            }),
            Widget.Button({
              class_name: "palette-close",
              child: Widget.Label("×"),
              on_clicked: () => toggleAgentSelector(false),
            }),
          ],
        }),
        Widget.Scrollable({
          class_name: "palette-list",
          hscroll: "never",
          vscroll: "automatic",
          child: Widget.Box({
            vertical: true,
            spacing: 4,
            children: chatState.bind().as((state) => {
              const activeChat = state.chats.find((c) => c.id === state.activeTabId);
              return state.agents.map((agent) =>
                AgentItem(agent, agent.name === activeChat?.agent, setActiveAgent)
              );
            }),
          }),
        }),
      ],
    }),
  });
}

// ============================================
// UI Components - Messages
// ============================================

function CodeBlock(code, language = "") {
  return Widget.Box({
    class_name: "code-block",
    vertical: true,
    children: [
      Widget.Box({
        class_name: "code-header",
        children: [
          Widget.Label({
            class_name: "code-lang",
            label: language || "code",
          }),
          Widget.Button({
            class_name: "code-copy",
            child: Widget.Label(""),
            tooltip_text: "Copiar",
            on_clicked: () => {
              Utils.execAsync(["wl-copy", code]).catch(() =>
                Utils.execAsync(["xclip", "-selection", "clipboard"]).catch(() => {})
              );
            },
          }),
        ],
      }),
      Widget.Label({
        class_name: "code-content",
        label: code,
        selectable: true,
        xalign: 0,
        wrap: false,
      }),
    ],
  });
}

function parseMessageContent(content) {
  const parts = [];
  // Match code blocks but exclude tool blocks
  const codeBlockRegex = /```(?!tool:)(\w*)\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: "text",
        content: content.slice(lastIndex, match.index),
      });
    }

    parts.push({
      type: "code",
      language: match[1],
      content: match[2].trim(),
    });

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({
      type: "text",
      content: content.slice(lastIndex),
    });
  }

  return parts.length ? parts : [{ type: "text", content }];
}

function MessageContent(content) {
  const parts = parseMessageContent(content);

  return Widget.Box({
    vertical: true,
    spacing: 8,
    children: parts.map((part) => {
      if (part.type === "code") {
        return CodeBlock(part.content, part.language);
      }
      return Widget.Label({
        class_name: "message-text",
        label: part.content.trim(),
        wrap: true,
        xalign: 0,
        selectable: true,
        use_markup: false,
      });
    }),
  });
}

function ActionResult(action) {
  const icon = action.success ? "" : "";
  const statusClass = action.success ? "success" : "error";

  return Widget.Box({
    class_name: `action-result ${statusClass}`,
    vertical: true,
    children: [
      Widget.Box({
        spacing: 6,
        children: [
          Widget.Label({
            class_name: `action-icon ${statusClass}`,
            label: icon,
          }),
          Widget.Label({
            class_name: "action-type",
            label: action.type,
          }),
          Widget.Label({
            class_name: "action-desc",
            label: action.description,
            hexpand: true,
            xalign: 0,
            truncate: "end",
          }),
        ],
      }),
      ...(action.output
        ? [
            Widget.Label({
              class_name: "action-output",
              label: action.output.slice(0, 200) + (action.output.length > 200 ? "..." : ""),
              xalign: 0,
              wrap: true,
              selectable: true,
            }),
          ]
        : []),
    ],
  });
}

function Message(msg) {
  const isUser = msg.role === "user";
  const isError = msg.role === "error";

  const time = new Date(msg.timestamp).toLocaleTimeString("es", {
    hour: "2-digit",
    minute: "2-digit",
  });

  // Get agent info for icon
  const agentInfo = chatState.value.agents.find((a) => a.name === msg.agent);
  const agentIcon = agentInfo?.icon || "󰚩";

  const avatar = Widget.Box({
    class_name: `avatar ${msg.role}`,
    child: Widget.Label({
      label: isUser ? "" : isError ? "" : agentIcon,
    }),
  });

  const header = Widget.Box({
    class_name: "message-header",
    spacing: 8,
    children: [
      Widget.Label({
        class_name: "message-sender",
        label: isUser ? "Tú" : isError ? "Error" : msg.agent || "Purma",
      }),
      Widget.Label({
        class_name: "message-time",
        label: time,
      }),
      ...(msg.model
        ? [
            Widget.Label({
              class_name: "message-model",
              label: msg.model,
            }),
          ]
        : []),
    ],
  });

  const content = Widget.Box({
    class_name: "message-body",
    vertical: true,
    spacing: 8,
    children: [
      MessageContent(msg.content),
      ...(msg.actions?.length
        ? [
            Widget.Box({
              class_name: "actions-container",
              vertical: true,
              spacing: 4,
              children: msg.actions.map(ActionResult),
            }),
          ]
        : []),
    ],
  });

  return Widget.Box({
    class_name: `message ${msg.role}`,
    spacing: 12,
    children: [avatar, Widget.Box({ vertical: true, hexpand: true, children: [header, content] })],
  });
}

function LoadingMessage() {
  const activeChat = getActiveChat();
  const agentInfo = chatState.value.agents.find((a) => a.name === activeChat?.agent);
  const agentIcon = agentInfo?.icon || "󰚩";

  return Widget.Box({
    class_name: "message assistant loading",
    spacing: 12,
    children: [
      Widget.Box({
        class_name: "avatar assistant",
        child: Widget.Label({ label: agentIcon }),
      }),
      Widget.Box({
        vertical: true,
        children: [
          Widget.Box({
            class_name: "message-header",
            children: [
              Widget.Label({
                class_name: "message-sender",
                label: activeChat?.agent || "Purma",
              }),
            ],
          }),
          Widget.Box({
            class_name: "loading-dots",
            children: [
              Widget.Label({ class_name: "dot", label: "●" }),
              Widget.Label({ class_name: "dot delay-1", label: "●" }),
              Widget.Label({ class_name: "dot delay-2", label: "●" }),
            ],
          }),
        ],
      }),
    ],
  });
}

function MessagesArea() {
  return Widget.Scrollable({
    class_name: "messages-area",
    hscroll: "never",
    vscroll: "automatic",
    vexpand: true,
    child: Widget.Box({
      vertical: true,
      class_name: "messages-container",
      children: chatState.bind().as((state) => {
        const activeChat = state.chats.find((c) => c.id === state.activeTabId);
        if (!activeChat) return [];

        const messages = activeChat.messages.map(Message);
        if (state.isLoading) {
          messages.push(LoadingMessage());
        }
        return messages;
      }),
    }),
    setup: (self) => {
      self.hook(chatState, () => {
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
          const adj = self.get_vadjustment();
          adj.set_value(adj.get_upper());
          return false;
        });
      });
    },
  });
}

// ============================================
// UI Components - Welcome Screen
// ============================================

function WelcomeScreen() {
  const suggestions = [
    { icon: "", text: "Organiza mis descargas", cmd: "/organize ~/Downloads" },
    { icon: "", text: "Busca imágenes", cmd: "/search perro type=images" },
    { icon: "", text: "Info del sistema", cmd: "/disk" },
    { icon: "", text: "Crea un script", cmd: "/script description=\"lista archivos grandes\"" },
  ];

  return Widget.Box({
    class_name: "welcome-screen",
    vertical: true,
    vexpand: true,
    vpack: "center",
    hpack: "center",
    visible: chatState.bind().as((state) => {
      const activeChat = state.chats.find((c) => c.id === state.activeTabId);
      return !activeChat?.messages.length;
    }),
    children: [
      Widget.Label({
        class_name: "welcome-icon",
        label: "󰚩",
      }),
      Widget.Label({
        class_name: "welcome-title",
        label: "Purma AI",
      }),
      Widget.Label({
        class_name: "welcome-subtitle",
        label: "Tu asistente local de IA",
      }),
      Widget.Box({
        class_name: "suggestions",
        vertical: true,
        spacing: 8,
        children: suggestions.map((s) =>
          Widget.Button({
            class_name: "suggestion",
            on_clicked: () => sendMessage(s.cmd),
            child: Widget.Box({
              spacing: 12,
              children: [
                Widget.Label({ class_name: "suggestion-icon", label: s.icon }),
                Widget.Label({ class_name: "suggestion-text", label: s.text }),
              ],
            }),
          })
        ),
      }),
      Widget.Box({
        class_name: "welcome-hint",
        spacing: 8,
        children: [
          Widget.Label({
            class_name: "hint-text",
            label: "Usa",
          }),
          Widget.Label({
            class_name: "hint-key",
            label: "/",
          }),
          Widget.Label({
            class_name: "hint-text",
            label: "para comandos o",
          }),
          Widget.Label({
            class_name: "hint-key",
            label: "@",
          }),
          Widget.Label({
            class_name: "hint-text",
            label: "para agentes",
          }),
        ],
      }),
    ],
  });
}

// ============================================
// UI Components - Input
// ============================================

function AgentBadge() {
  return Widget.Button({
    class_name: "agent-badge",
    on_clicked: () => toggleAgentSelector(),
    child: Widget.Box({
      spacing: 4,
      children: [
        Widget.Label({
          class_name: "agent-badge-icon",
          label: chatState.bind().as((state) => {
            const activeChat = state.chats.find((c) => c.id === state.activeTabId);
            const agent = state.agents.find((a) => a.name === activeChat?.agent);
            return agent?.icon || "󰚩";
          }),
        }),
        Widget.Label({
          class_name: "agent-badge-name",
          label: chatState.bind().as((state) => {
            const activeChat = state.chats.find((c) => c.id === state.activeTabId);
            return activeChat?.agent || "purma";
          }),
        }),
        Widget.Label({
          class_name: "agent-badge-arrow",
          label: "",
        }),
      ],
    }),
  });
}

function InputArea() {
  let entry;

  const sendButton = Widget.Button({
    class_name: "send-button",
    child: Widget.Label(""),
    sensitive: chatState.bind().as((s) => !s.isLoading),
    on_clicked: () => {
      const text = entry.text.trim();
      if (text) {
        sendMessage(text);
        entry.text = "";
      }
    },
  });

  entry = Widget.Entry({
    class_name: "chat-input",
    hexpand: true,
    placeholder_text: "Escribe un mensaje... (/ comandos, @ agentes)",
    on_accept: () => {
      const text = entry.text.trim();
      if (text && !chatState.value.isLoading) {
        sendMessage(text);
        entry.text = "";
      }
    },
    setup: (self) => {
      self.connect("changed", () => {
        const text = self.text;
        // Show command palette when typing /
        if (text === "/") {
          toggleCommandPalette(true);
        } else if (text.startsWith("@") && text.length === 1) {
          toggleAgentSelector(true);
        } else if (!text.startsWith("/") && !text.startsWith("@")) {
          toggleCommandPalette(false);
          toggleAgentSelector(false);
        }
      });
    },
  });

  return Widget.Box({
    class_name: "input-area",
    vertical: true,
    children: [
      Widget.Box({
        class_name: "input-row",
        spacing: 8,
        children: [
          AgentBadge(),
          Widget.Box({
            class_name: "input-container",
            hexpand: true,
            children: [entry],
          }),
          sendButton,
        ],
      }),
    ],
  });
}

// ============================================
// UI Components - Footer
// ============================================

function Footer() {
  return Widget.Box({
    class_name: "chat-footer",
    children: [
      Widget.Label({
        class_name: "footer-text",
        label: chatState.bind().as((state) => {
          const activeChat = state.chats.find((c) => c.id === state.activeTabId);
          return `Purma AI • ${activeChat?.agent || "purma"} • ~/`;
        }),
        hexpand: true,
        xalign: 0,
      }),
      Widget.Button({
        class_name: "footer-btn",
        child: Widget.Label(""),
        tooltip_text: "Recargar agentes",
        on_clicked: () => {
          Utils.fetch(`${PURMA_SERVER}/reload`, { method: "POST" })
            .then(() => loadAgentsAndCommands())
            .catch(console.error);
        },
      }),
      Widget.Button({
        class_name: "footer-btn",
        child: Widget.Label(""),
        tooltip_text: "Terminal",
        on_clicked: () => Utils.execAsync(["kitty", "-e", "ollama", "run", "purma"]),
      }),
    ],
  });
}

// ============================================
// Main Chat Panel
// ============================================

function ChatPanel() {
  return Widget.Box({
    class_name: "chat-panel",
    vertical: true,
    children: [
      ChatHeader(),
      TabBar(),
      CommandPalette(),
      AgentSelector(),
      Widget.Box({
        class_name: "chat-content",
        vertical: true,
        vexpand: true,
        children: [WelcomeScreen(), MessagesArea()],
      }),
      InputArea(),
      Footer(),
    ],
  });
}

// ============================================
// Window Export
// ============================================

export function ChatWindow(monitor = 0) {
  // Initial load
  GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
    loadAgentsAndCommands();
    return false;
  });

  // Periodic status check
  GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 30, () => {
    if (chatState.value.isVisible) {
      checkServerStatus();
    }
    return true;
  });

  return Widget.Window({
    name: `purma-chat-${monitor}`,
    class_name: "purma-chat-window",
    monitor,
    anchor: ["top", "right", "bottom"],
    exclusivity: "normal",
    layer: "top",
    visible: chatState.bind().as((s) => s.isVisible),
    keymode: "on-demand",
    child: ChatPanel(),
    setup: (self) => {
      self.keybind("Escape", () => {
        if (chatState.value.showCommandPalette || chatState.value.showAgentSelector) {
          toggleCommandPalette(false);
          toggleAgentSelector(false);
        } else {
          toggleChat();
        }
      });
    },
  });
}

export { toggleChat };
globalThis.togglePurmaChat = toggleChat;
