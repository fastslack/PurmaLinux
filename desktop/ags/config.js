/**
 * PurmaLinux Desktop - AGS Configuration
 * Barra superior + Chat AI Sidebar
 */

import { ChatWindow, toggleChat } from "./widgets/chat/Chat.js";
import { SpacesWindow, SpacesButton, toggleSpaces } from "./widgets/spaces/Spaces.js";
import { FlowWindow, FlowButton, toggleFlow, toggleRecording } from "./widgets/flow/Flow.js";
import { BridgeWindow, BridgeButton, toggleBridge } from "./widgets/bridge/Bridge.js";
import { PulseWindow, PulseButton, togglePulse } from "./widgets/pulse/Pulse.js";
import { LensWindow, LensButton, toggleLens, quickCapture } from "./widgets/lens/Lens.js";
import { VaultWindow, VaultButton, toggleVault } from "./widgets/vault/Vault.js";
import { ScribeWindow, ScribeButton, toggleScribe } from "./widgets/scribe/Scribe.js";
import { BrainWindow, BrainButton, toggleBrain } from "./widgets/brain/Brain.js";

const notifications = await Service.import("notifications");
const mpris = await Service.import("mpris");
const audio = await Service.import("audio");
const battery = await Service.import("battery");
const systemtray = await Service.import("systemtray");
const network = await Service.import("network");
const bluetooth = await Service.import("bluetooth");

const date = Variable("", {
  poll: [1000, 'date "+%a %d %b  %H:%M"'],
});

// ============================================
// Widgets
// ============================================

function Launcher() {
  return Widget.Button({
    class_name: "launcher",
    child: Widget.Label(""),
    on_clicked: () => Utils.execAsync("rofi -show drun"),
  });
}

function Workspaces() {
  const workspaces = [1, 2, 3, 4];

  return Widget.Box({
    class_name: "workspaces",
    children: workspaces.map((ws) =>
      Widget.Button({
        class_name: "workspace",
        label: `${ws}`,
        on_clicked: () => Utils.execAsync(`wmctrl -s ${ws - 1}`),
      })
    ),
  });
}

function ActiveWindow() {
  return Widget.Label({
    class_name: "active-window",
    label: "PurmaLinux",
    max_width_chars: 50,
    truncate: "end",
  });
}

// AI Button - Abre el Chat Sidebar
function AIButton() {
  return Widget.Button({
    class_name: "ai-button",
    child: Widget.Box({
      children: [
        Widget.Label({ label: "󰚩" }),
        Widget.Label({ label: " Purma AI" }),
      ],
    }),
    on_clicked: () => toggleChat(),
    tooltip_text: "Abrir Purma AI (Super+A)",
  });
}

function SysTray() {
  const items = systemtray.bind("items").as((items) =>
    items.map((item) =>
      Widget.Button({
        class_name: "tray-item",
        child: Widget.Icon({ icon: item.bind("icon") }),
        on_primary_click: (_, event) => item.activate(event),
        on_secondary_click: (_, event) => item.openMenu(event),
        tooltip_markup: item.bind("tooltip_markup"),
      })
    )
  );

  return Widget.Box({
    class_name: "systray",
    children: items,
  });
}

function Network() {
  const wifiIndicator = Widget.Box({
    children: [
      Widget.Icon({
        icon: network.wifi.bind("icon_name"),
      }),
      Widget.Label({
        label: network.wifi.bind("ssid").as((ssid) => ssid || ""),
        visible: network.wifi.bind("ssid").as((ssid) => !!ssid),
      }),
    ],
  });

  const wiredIndicator = Widget.Icon({
    icon: network.wired.bind("icon_name"),
  });

  return Widget.Stack({
    class_name: "network",
    children: {
      wifi: wifiIndicator,
      wired: wiredIndicator,
    },
    shown: network.bind("primary").as((p) => p || "wifi"),
  });
}

function Bluetooth() {
  return Widget.Button({
    class_name: "bluetooth",
    visible: bluetooth.bind("enabled"),
    child: Widget.Icon({
      icon: bluetooth
        .bind("connected_devices")
        .as((c) => (c.length > 0 ? "bluetooth-active-symbolic" : "bluetooth-symbolic")),
    }),
    on_clicked: () => Utils.execAsync("blueman-manager"),
  });
}

function Volume() {
  const icons = {
    101: "overamplified",
    67: "high",
    34: "medium",
    1: "low",
    0: "muted",
  };

  function getIcon() {
    const icon = audio.speaker.is_muted
      ? 0
      : [101, 67, 34, 1, 0].find((threshold) => threshold <= audio.speaker.volume * 100);
    return `audio-volume-${icons[icon]}-symbolic`;
  }

  const icon = Widget.Button({
    child: Widget.Icon({
      icon: Utils.watch(getIcon(), audio.speaker, getIcon),
    }),
    on_clicked: () => (audio.speaker.is_muted = !audio.speaker.is_muted),
  });

  const slider = Widget.Slider({
    class_name: "volume-slider",
    hexpand: true,
    draw_value: false,
    on_change: ({ value }) => (audio.speaker.volume = value),
    setup: (self) =>
      self.hook(audio.speaker, () => {
        self.value = audio.speaker.volume || 0;
      }),
  });

  return Widget.Box({
    class_name: "volume",
    children: [icon, slider],
  });
}

function BatteryWidget() {
  const icon = battery.bind("percent").as((p) => `battery-level-${Math.floor(p / 10) * 10}-symbolic`);

  return Widget.Box({
    class_name: "battery",
    visible: battery.bind("available"),
    children: [
      Widget.Icon({ icon }),
      Widget.Label({
        label: battery.bind("percent").as((p) => `${p}%`),
      }),
    ],
  });
}

function Clock() {
  return Widget.Button({
    class_name: "clock",
    child: Widget.Label({
      label: date.bind(),
    }),
  });
}

function PowerButton() {
  return Widget.Button({
    class_name: "power-button",
    child: Widget.Label("⏻"),
    on_clicked: () => Utils.execAsync("rofi -show power-menu -modi power-menu:rofi-power-menu"),
  });
}

function Media() {
  const player = mpris.bind("players").as((p) => p[0] || null);

  return Widget.Box({
    class_name: "media",
    visible: player.as((p) => !!p),
    children: [
      Widget.Label({
        label: player.as((p) => {
          if (!p) return "";
          const title = p.track_title || "Unknown";
          const artist = p.track_artists?.join(", ") || "";
          return artist ? `${artist} - ${title}` : title;
        }),
        max_width_chars: 30,
        truncate: "end",
      }),
      Widget.Button({
        child: Widget.Label("⏮"),
        on_clicked: () => mpris.players[0]?.previous(),
      }),
      Widget.Button({
        child: Widget.Label({
          label: player.as((p) => (p?.play_back_status === "Playing" ? "⏸" : "▶")),
        }),
        on_clicked: () => mpris.players[0]?.playPause(),
      }),
      Widget.Button({
        child: Widget.Label("⏭"),
        on_clicked: () => mpris.players[0]?.next(),
      }),
    ],
  });
}

// ============================================
// Bar
// ============================================

function Left() {
  return Widget.Box({
    class_name: "bar-left",
    spacing: 8,
    children: [Launcher(), Workspaces(), ActiveWindow()],
  });
}

function Center() {
  return Widget.Box({
    class_name: "bar-center",
    spacing: 8,
    children: [Media()],
  });
}

function Right() {
  return Widget.Box({
    class_name: "bar-right",
    hpack: "end",
    spacing: 8,
    children: [
      LensButton(),
      PulseButton(),
      BridgeButton(),
      FlowButton(),
      SpacesButton(),
      BrainButton(),
      VaultButton(),
      ScribeButton(),
      AIButton(),
      SysTray(),
      Network(),
      Bluetooth(),
      Volume(),
      BatteryWidget(),
      Clock(),
      PowerButton(),
    ],
  });
}

function Bar(monitor = 0) {
  return Widget.Window({
    name: `bar-${monitor}`,
    class_name: "bar",
    monitor,
    anchor: ["top", "left", "right"],
    exclusivity: "exclusive",
    child: Widget.CenterBox({
      start_widget: Left(),
      center_widget: Center(),
      end_widget: Right(),
    }),
  });
}

// ============================================
// Notifications
// ============================================

function NotificationPopups(monitor = 0) {
  const list = Widget.Box({
    vertical: true,
    children: notifications.bind("popups").as((popups) =>
      popups.map((n) =>
        Widget.Box({
          class_name: `notification ${n.urgency}`,
          vertical: true,
          children: [
            Widget.Box({
              children: [
                Widget.Label({
                  class_name: "title",
                  label: n.summary,
                  xalign: 0,
                  hexpand: true,
                }),
                Widget.Button({
                  child: Widget.Label("✕"),
                  on_clicked: () => n.close(),
                }),
              ],
            }),
            Widget.Label({
              class_name: "body",
              label: n.body,
              xalign: 0,
              wrap: true,
            }),
          ],
        })
      )
    ),
  });

  return Widget.Window({
    name: `notifications-${monitor}`,
    class_name: "notification-popups",
    monitor,
    anchor: ["top", "right"],
    child: Widget.Box({
      css: "min-width: 2px; min-height: 2px;",
      vertical: true,
      child: list,
    }),
  });
}

// ============================================
// Global keybind for chat toggle (Super+A handled by WM, but also dbus)
// ============================================
Utils.execAsync([
  "dbus-send",
  "--session",
  "--dest=org.freedesktop.DBus",
  "--type=method_call",
  "/org/freedesktop/DBus",
  "org.freedesktop.DBus.ListNames",
]).catch(() => {});

// Export toggle functions for external use
globalThis.togglePurmaChat = toggleChat;
globalThis.togglePurmaSpaces = toggleSpaces;
globalThis.togglePurmaFlow = toggleFlow;
globalThis.togglePurmaRecording = toggleRecording;
globalThis.togglePurmaBridge = toggleBridge;
globalThis.togglePurmaPulse = togglePulse;
globalThis.togglePurmaLens = toggleLens;
globalThis.purmaQuickCapture = quickCapture;
globalThis.togglePurmaVault = toggleVault;
globalThis.togglePurmaScribe = toggleScribe;
globalThis.togglePurmaBrain = toggleBrain;

// ============================================
// App Config
// ============================================

App.config({
  style: [
    "./style.css",
    "./widgets/chat/style.css",
    "./widgets/spaces/style.css",
    "./widgets/flow/style.css",
    "./widgets/bridge/style.css",
    "./widgets/pulse/style.css",
    "./widgets/lens/style.css",
    "./widgets/vault/style.css",
    "./widgets/scribe/style.css",
    "./widgets/brain/style.css",
  ].join("\n@import url('") + "');",
  windows: [
    Bar(),
    NotificationPopups(),
    ChatWindow(),
    SpacesWindow(),
    FlowWindow(),
    BridgeWindow(),
    PulseWindow(),
    LensWindow(),
    VaultWindow(),
    ScribeWindow(),
    BrainWindow(),
  ],
});

export {};
