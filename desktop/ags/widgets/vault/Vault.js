/**
 * PurmaLinux - Vault Widget
 * AI-Powered Password Manager
 */

const API_BASE = "http://localhost:11435";

// State management
const vaultState = Variable({
  visible: false,
  unlocked: false,
  initialized: false,
  secrets: [],
  searchQuery: "",
  selectedSecret: null,
  view: "main", // main, unlock, search, add, generate
  loading: false,
  error: null,
  generatedPassword: null,
});

// API Functions
async function fetchVaultStatus() {
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/status`);
    const data = JSON.parse(response);
    vaultState.value = {
      ...vaultState.value,
      initialized: data.initialized,
      unlocked: data.unlocked,
      view: data.unlocked ? "main" : (data.initialized ? "unlock" : "init"),
    };
    if (data.unlocked) {
      await fetchSecrets();
    }
  } catch (e) {
    console.error("Vault status error:", e);
  }
}

async function fetchSecrets() {
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/secrets`);
    const data = JSON.parse(response);
    vaultState.value = { ...vaultState.value, secrets: data.secrets || [] };
  } catch (e) {
    console.error("Fetch secrets error:", e);
  }
}

async function unlockVault(password) {
  vaultState.value = { ...vaultState.value, loading: true, error: null };
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = JSON.parse(response);
    if (data.success) {
      vaultState.value = { ...vaultState.value, unlocked: true, view: "main", loading: false };
      await fetchSecrets();
    }
  } catch (e) {
    vaultState.value = { ...vaultState.value, error: "Invalid password", loading: false };
  }
}

async function initVault(password) {
  vaultState.value = { ...vaultState.value, loading: true, error: null };
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = JSON.parse(response);
    if (data.success) {
      vaultState.value = { ...vaultState.value, initialized: true, unlocked: true, view: "main", loading: false };
    }
  } catch (e) {
    vaultState.value = { ...vaultState.value, error: "Failed to initialize vault", loading: false };
  }
}

async function lockVault() {
  try {
    await Utils.fetch(`${API_BASE}/vault/lock`, { method: "POST" });
    vaultState.value = { ...vaultState.value, unlocked: false, view: "unlock", secrets: [] };
  } catch (e) {
    console.error("Lock error:", e);
  }
}

async function searchSecrets(query) {
  if (!query) {
    await fetchSecrets();
    return;
  }
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/search?q=${encodeURIComponent(query)}`);
    const data = JSON.parse(response);
    vaultState.value = { ...vaultState.value, secrets: data.results || [] };
  } catch (e) {
    console.error("Search error:", e);
  }
}

async function getSecret(secretId) {
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/secrets/${secretId}`);
    const data = JSON.parse(response);
    vaultState.value = { ...vaultState.value, selectedSecret: data };
    // Copy to clipboard
    Utils.execAsync(["wl-copy", data.decrypted_value || ""]);
  } catch (e) {
    console.error("Get secret error:", e);
  }
}

async function generatePassword(length = 20) {
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/generate?length=${length}`);
    const data = JSON.parse(response);
    vaultState.value = { ...vaultState.value, generatedPassword: data };
    Utils.execAsync(["wl-copy", data.password]);
  } catch (e) {
    console.error("Generate password error:", e);
  }
}

async function addSecret(name, value, username, url, category) {
  vaultState.value = { ...vaultState.value, loading: true };
  try {
    const response = await Utils.fetch(`${API_BASE}/vault/secrets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, value, username, url, category }),
    });
    const data = JSON.parse(response);
    if (data.success) {
      vaultState.value = { ...vaultState.value, view: "main", loading: false };
      await fetchSecrets();
    }
  } catch (e) {
    vaultState.value = { ...vaultState.value, error: "Failed to add secret", loading: false };
  }
}

// UI Components
function VaultHeader() {
  return Widget.Box({
    class_name: "vault-header",
    children: [
      Widget.Box({
        hexpand: true,
        children: [
          Widget.Label({ class_name: "vault-icon", label: "🔐" }),
          Widget.Label({ class_name: "vault-title", label: "Purma Vault" }),
        ],
      }),
      Widget.Button({
        class_name: "header-btn lock-btn",
        child: Widget.Label({ label: vaultState.bind().as(s => s.unlocked ? "🔓" : "🔒") }),
        on_clicked: () => {
          if (vaultState.value.unlocked) lockVault();
        },
        tooltip_text: "Lock Vault",
      }),
      Widget.Button({
        class_name: "header-btn close-btn",
        child: Widget.Label({ label: "✕" }),
        on_clicked: () => toggleVault(),
      }),
    ],
  });
}

function UnlockView() {
  let passwordEntry;

  return Widget.Box({
    class_name: "unlock-view",
    vertical: true,
    vexpand: true,
    vpack: "center",
    children: [
      Widget.Label({ class_name: "unlock-icon", label: "🔒" }),
      Widget.Label({
        class_name: "unlock-title",
        label: vaultState.bind().as(s => s.initialized ? "Enter Master Password" : "Create Master Password"),
      }),
      Widget.Entry({
        class_name: "password-entry",
        placeholder_text: "Master password...",
        visibility: false,
        setup: (self) => { passwordEntry = self; },
        on_accept: () => {
          const password = passwordEntry.text;
          if (password) {
            if (vaultState.value.initialized) {
              unlockVault(password);
            } else {
              initVault(password);
            }
          }
        },
      }),
      Widget.Label({
        class_name: "error-text",
        visible: vaultState.bind().as(s => !!s.error),
        label: vaultState.bind().as(s => s.error || ""),
      }),
      Widget.Button({
        class_name: "unlock-btn",
        child: Widget.Label({
          label: vaultState.bind().as(s =>
            s.loading ? "..." : (s.initialized ? "Unlock" : "Initialize")
          ),
        }),
        on_clicked: () => {
          const password = passwordEntry.text;
          if (password) {
            if (vaultState.value.initialized) {
              unlockVault(password);
            } else {
              initVault(password);
            }
          }
        },
      }),
    ],
  });
}

function SearchBar() {
  return Widget.Box({
    class_name: "search-bar",
    children: [
      Widget.Label({ class_name: "search-icon", label: "" }),
      Widget.Entry({
        class_name: "search-entry",
        hexpand: true,
        placeholder_text: "Search passwords...",
        on_change: ({ text }) => {
          vaultState.value = { ...vaultState.value, searchQuery: text };
          searchSecrets(text);
        },
      }),
      Widget.Button({
        class_name: "add-btn",
        child: Widget.Label({ label: "+" }),
        on_clicked: () => {
          vaultState.value = { ...vaultState.value, view: "add" };
        },
        tooltip_text: "Add Password",
      }),
      Widget.Button({
        class_name: "generate-btn",
        child: Widget.Label({ label: "🎲" }),
        on_clicked: () => {
          vaultState.value = { ...vaultState.value, view: "generate" };
        },
        tooltip_text: "Generate Password",
      }),
    ],
  });
}

function SecretItem(secret) {
  const typeIcons = {
    password: "🔑",
    api_key: "🔧",
    ssh_key: "🖥️",
    credit_card: "💳",
    secure_note: "📝",
    identity: "👤",
  };

  return Widget.Button({
    class_name: "secret-item",
    on_clicked: () => getSecret(secret.id),
    child: Widget.Box({
      children: [
        Widget.Label({
          class_name: "secret-icon",
          label: typeIcons[secret.secret_type] || "🔐",
        }),
        Widget.Box({
          vertical: true,
          hexpand: true,
          children: [
            Widget.Label({
              class_name: "secret-name",
              label: secret.name,
              xalign: 0,
              truncate: "end",
            }),
            Widget.Label({
              class_name: "secret-username",
              label: secret.username || secret.category,
              xalign: 0,
            }),
          ],
        }),
        Widget.Label({
          class_name: "secret-favorite",
          label: secret.favorite ? "⭐" : "",
        }),
        Widget.Label({ class_name: "copy-icon", label: "📋" }),
      ],
    }),
  });
}

function SecretsList() {
  return Widget.Scrollable({
    class_name: "secrets-list",
    vexpand: true,
    child: Widget.Box({
      vertical: true,
      children: vaultState.bind().as(s => {
        if (s.secrets.length === 0) {
          return [
            Widget.Box({
              class_name: "empty-state",
              vertical: true,
              vexpand: true,
              vpack: "center",
              children: [
                Widget.Label({ class_name: "empty-icon", label: "🔐" }),
                Widget.Label({ class_name: "empty-title", label: "No passwords yet" }),
                Widget.Label({ class_name: "empty-hint", label: "Click + to add your first password" }),
              ],
            }),
          ];
        }
        return s.secrets.map(secret => SecretItem(secret));
      }),
    }),
  });
}

function GenerateView() {
  let lengthEntry;

  return Widget.Box({
    class_name: "generate-view",
    vertical: true,
    children: [
      Widget.Button({
        class_name: "back-btn",
        child: Widget.Label({ label: "← Back" }),
        on_clicked: () => {
          vaultState.value = { ...vaultState.value, view: "main", generatedPassword: null };
        },
      }),
      Widget.Label({ class_name: "view-title", label: "🎲 Generate Password" }),
      Widget.Box({
        class_name: "generate-options",
        children: [
          Widget.Label({ label: "Length:" }),
          Widget.Entry({
            class_name: "length-entry",
            text: "20",
            setup: (self) => { lengthEntry = self; },
          }),
        ],
      }),
      Widget.Button({
        class_name: "generate-action-btn",
        child: Widget.Label({ label: "Generate" }),
        on_clicked: () => generatePassword(parseInt(lengthEntry.text) || 20),
      }),
      Widget.Box({
        class_name: "generated-result",
        vertical: true,
        visible: vaultState.bind().as(s => !!s.generatedPassword),
        children: [
          Widget.Label({
            class_name: "generated-password",
            label: vaultState.bind().as(s => s.generatedPassword?.password || ""),
            selectable: true,
          }),
          Widget.Label({
            class_name: "password-strength",
            label: vaultState.bind().as(s => {
              const strength = s.generatedPassword?.strength;
              if (!strength) return "";
              return `Strength: ${strength.level.toUpperCase()} (${strength.score}/${strength.max_score})`;
            }),
          }),
          Widget.Label({ class_name: "copied-hint", label: "✓ Copied to clipboard" }),
        ],
      }),
    ],
  });
}

function AddSecretView() {
  let nameEntry, valueEntry, usernameEntry, urlEntry;

  return Widget.Box({
    class_name: "add-view",
    vertical: true,
    children: [
      Widget.Button({
        class_name: "back-btn",
        child: Widget.Label({ label: "← Back" }),
        on_clicked: () => {
          vaultState.value = { ...vaultState.value, view: "main" };
        },
      }),
      Widget.Label({ class_name: "view-title", label: "➕ Add Password" }),
      Widget.Box({
        class_name: "form-field",
        vertical: true,
        children: [
          Widget.Label({ class_name: "field-label", label: "Name *", xalign: 0 }),
          Widget.Entry({
            class_name: "form-entry",
            placeholder_text: "e.g., Netflix",
            setup: (self) => { nameEntry = self; },
          }),
        ],
      }),
      Widget.Box({
        class_name: "form-field",
        vertical: true,
        children: [
          Widget.Label({ class_name: "field-label", label: "Password *", xalign: 0 }),
          Widget.Entry({
            class_name: "form-entry",
            placeholder_text: "Password",
            visibility: false,
            setup: (self) => { valueEntry = self; },
          }),
        ],
      }),
      Widget.Box({
        class_name: "form-field",
        vertical: true,
        children: [
          Widget.Label({ class_name: "field-label", label: "Username", xalign: 0 }),
          Widget.Entry({
            class_name: "form-entry",
            placeholder_text: "email@example.com",
            setup: (self) => { usernameEntry = self; },
          }),
        ],
      }),
      Widget.Box({
        class_name: "form-field",
        vertical: true,
        children: [
          Widget.Label({ class_name: "field-label", label: "URL", xalign: 0 }),
          Widget.Entry({
            class_name: "form-entry",
            placeholder_text: "https://...",
            setup: (self) => { urlEntry = self; },
          }),
        ],
      }),
      Widget.Button({
        class_name: "save-btn",
        child: Widget.Label({ label: vaultState.bind().as(s => s.loading ? "Saving..." : "Save") }),
        on_clicked: () => {
          const name = nameEntry.text;
          const value = valueEntry.text;
          if (name && value) {
            addSecret(name, value, usernameEntry.text, urlEntry.text, "General");
          }
        },
      }),
    ],
  });
}

function MainView() {
  return Widget.Box({
    class_name: "main-view",
    vertical: true,
    children: [
      SearchBar(),
      SecretsList(),
    ],
  });
}

function VaultContent() {
  return Widget.Box({
    class_name: "vault-content",
    vertical: true,
    vexpand: true,
    children: vaultState.bind().as(s => {
      if (!s.unlocked) {
        return [UnlockView()];
      }

      switch (s.view) {
        case "generate":
          return [GenerateView()];
        case "add":
          return [AddSecretView()];
        default:
          return [MainView()];
      }
    }),
  });
}

// Main Window
export function VaultWindow() {
  return Widget.Window({
    name: "purma-vault",
    class_name: "vault-window",
    anchor: ["top", "right"],
    exclusivity: "normal",
    layer: "overlay",
    margins: [60, 16, 16, 16],
    visible: vaultState.bind().as(s => s.visible),
    child: Widget.Box({
      class_name: "vault-popup",
      vertical: true,
      children: [
        VaultHeader(),
        VaultContent(),
      ],
    }),
    setup: () => {
      fetchVaultStatus();
    },
  });
}

// Bar Button
export function VaultButton() {
  return Widget.Button({
    class_name: "vault-button",
    child: Widget.Box({
      children: [
        Widget.Label({ class_name: "vault-btn-icon", label: "🔐" }),
        Widget.Label({ class_name: "vault-btn-label", label: " Vault" }),
      ],
    }),
    on_clicked: () => toggleVault(),
    tooltip_text: "Purma Vault (Super+V)",
  });
}

// Toggle function
export function toggleVault() {
  vaultState.value = { ...vaultState.value, visible: !vaultState.value.visible };
  if (vaultState.value.visible) {
    fetchVaultStatus();
  }
}

export { vaultState };
