/**
 * PurmaLinux - GameHub Widget
 * Centro unificado de gaming
 * Shortcut: Super+G
 */

const { Gtk, GLib } = imports.gi;

// ═══════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════

const API_URL = "http://localhost:11435/gamehub";

const gamehubState = Variable({
    visible: false,
    loading: false,
    activeTab: "recent", // recent, all, favorites, steam, lutris, heroic
    games: [],
    recentGames: [],
    favorites: [],
    searchQuery: "",
    searchResults: [],
    status: null,
    selectedGame: null,
    gamemodeActive: false,
});

// ═══════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════

async function fetchAPI(endpoint, method = "GET", body = null) {
    try {
        const options = {
            method,
            headers: { "Content-Type": "application/json" },
        };
        if (body) options.body = JSON.stringify(body);

        const response = await Utils.fetch(`${API_URL}${endpoint}`, options);
        return response;
    } catch (error) {
        console.error(`GameHub API Error: ${error}`);
        return null;
    }
}

async function loadStatus() {
    const data = await fetchAPI("/status");
    if (data) {
        gamehubState.value = {
            ...gamehubState.value,
            status: data,
            gamemodeActive: data.gamemode?.active || false,
        };
    }
}

async function loadRecentGames() {
    gamehubState.value = { ...gamehubState.value, loading: true };

    const data = await fetchAPI("/games/recent?limit=12");
    if (data?.games) {
        gamehubState.value = {
            ...gamehubState.value,
            recentGames: data.games,
            loading: false,
        };
    } else {
        gamehubState.value = { ...gamehubState.value, loading: false };
    }
}

async function loadAllGames(source = null) {
    gamehubState.value = { ...gamehubState.value, loading: true };

    const endpoint = source ? `/games?source=${source}` : "/games";
    const data = await fetchAPI(endpoint);

    if (data?.games) {
        gamehubState.value = {
            ...gamehubState.value,
            games: data.games,
            loading: false,
        };
    } else {
        gamehubState.value = { ...gamehubState.value, loading: false };
    }
}

async function loadFavorites() {
    const data = await fetchAPI("/games/favorites");
    if (data?.games) {
        gamehubState.value = {
            ...gamehubState.value,
            favorites: data.games,
        };
    }
}

async function scanGames() {
    gamehubState.value = { ...gamehubState.value, loading: true };

    const data = await fetchAPI("/scan", "POST");

    if (data?.success) {
        // Recargar juegos después de escanear
        await loadRecentGames();
        await loadAllGames();
        await loadStatus();
    }

    gamehubState.value = { ...gamehubState.value, loading: false };
}

async function searchGames(query) {
    if (!query || query.length < 2) {
        gamehubState.value = { ...gamehubState.value, searchResults: [] };
        return;
    }

    const data = await fetchAPI(`/search?q=${encodeURIComponent(query)}`);
    if (data?.games) {
        gamehubState.value = {
            ...gamehubState.value,
            searchResults: data.games,
        };
    }
}

async function launchGame(gameId, useGamemode = true, useMangohud = false) {
    const data = await fetchAPI(
        `/games/${gameId}/launch?gamemode=${useGamemode}&mangohud=${useMangohud}`,
        "POST"
    );

    if (data?.success) {
        // Cerrar GameHub después de lanzar
        toggleGameHub();
        // Notificar
        Utils.execAsync(["notify-send", "PurmaLinux GameHub", `Launching ${data.game.name}...`]);
    }
}

async function toggleFavorite(gameId) {
    const data = await fetchAPI(`/games/${gameId}/favorite`, "POST");
    if (data?.success) {
        // Recargar favoritos
        await loadFavorites();
        // Actualizar en la lista actual
        const state = gamehubState.value;
        const updateGame = (games) =>
            games.map((g) =>
                g.id === gameId ? { ...g, is_favorite: data.is_favorite } : g
            );

        gamehubState.value = {
            ...state,
            games: updateGame(state.games),
            recentGames: updateGame(state.recentGames),
        };
    }
}

// ═══════════════════════════════════════════════════════════════════
// UI COMPONENTS
// ═══════════════════════════════════════════════════════════════════

function SourceIcon(source) {
    const icons = {
        steam: "󰓓",
        lutris: "󰺵",
        heroic: "󰊗",
        bottles: "󱄮",
        native: "󰣇",
        custom: "󰊠",
    };
    return icons[source] || "󰊠";
}

function RatingBadge(rating) {
    const colors = {
        platinum: "rating-platinum",
        gold: "rating-gold",
        silver: "rating-silver",
        bronze: "rating-bronze",
        borked: "rating-borked",
        native: "rating-native",
        pending: "rating-pending",
    };

    const labels = {
        platinum: "Platinum",
        gold: "Gold",
        silver: "Silver",
        bronze: "Bronze",
        borked: "Borked",
        native: "Native",
        pending: "?",
    };

    return Widget.Label({
        className: `rating-badge ${colors[rating] || "rating-pending"}`,
        label: labels[rating] || "?",
    });
}

function GameCard(game) {
    const hasBanner = game.banner && GLib.file_test(game.banner, GLib.FileTest.EXISTS);

    return Widget.Button({
        className: "game-card",
        onClicked: () => launchGame(game.id),
        onSecondaryClick: () => {
            gamehubState.value = {
                ...gamehubState.value,
                selectedGame: game,
            };
        },
        child: Widget.Box({
            vertical: true,
            children: [
                // Banner/Cover
                Widget.Box({
                    className: "game-banner",
                    css: hasBanner
                        ? `background-image: url("${game.banner}");`
                        : "",
                    child: Widget.Box({
                        className: "game-banner-overlay",
                        children: [
                            // Source icon
                            Widget.Label({
                                className: "game-source-icon",
                                label: SourceIcon(game.source),
                            }),
                            // Favorite button
                            Widget.Button({
                                className: `game-favorite ${game.is_favorite ? "active" : ""}`,
                                label: game.is_favorite ? "󰋑" : "󰋕",
                                onClicked: (self, event) => {
                                    event.stopPropagation();
                                    toggleFavorite(game.id);
                                },
                            }),
                        ],
                    }),
                }),
                // Info
                Widget.Box({
                    className: "game-info",
                    vertical: true,
                    children: [
                        Widget.Label({
                            className: "game-title",
                            label: game.name,
                            truncate: "end",
                            maxWidthChars: 20,
                            xalign: 0,
                        }),
                        Widget.Box({
                            className: "game-meta",
                            children: [
                                RatingBadge(game.proton_rating),
                                Widget.Label({
                                    className: "game-playtime",
                                    label: game.playtime_hours > 0
                                        ? `${game.playtime_hours}h`
                                        : "",
                                }),
                            ],
                        }),
                    ],
                }),
            ],
        }),
    });
}

function GameList(games, emptyMessage = "No games found") {
    if (!games || games.length === 0) {
        return Widget.Box({
            className: "games-empty",
            vexpand: true,
            hexpand: true,
            child: Widget.Label({
                label: emptyMessage,
                className: "empty-message",
            }),
        });
    }

    return Widget.Scrollable({
        className: "games-scroll",
        vexpand: true,
        child: Widget.FlowBox({
            className: "games-grid",
            homogeneous: true,
            minChildrenPerLine: 3,
            maxChildrenPerLine: 6,
            selectionMode: Gtk.SelectionMode.NONE,
            setup: (self) => {
                games.forEach((game) => {
                    self.add(GameCard(game));
                });
            },
        }),
    });
}

function TabButton(label, icon, tabId) {
    return Widget.Button({
        className: gamehubState.bind().as((s) =>
            `tab-btn ${s.activeTab === tabId ? "active" : ""}`
        ),
        onClicked: () => {
            gamehubState.value = {
                ...gamehubState.value,
                activeTab: tabId,
                searchQuery: "",
            };

            // Cargar datos según tab
            if (tabId === "recent") loadRecentGames();
            else if (tabId === "favorites") loadFavorites();
            else if (tabId === "all") loadAllGames();
            else if (["steam", "lutris", "heroic"].includes(tabId))
                loadAllGames(tabId);
        },
        child: Widget.Box({
            children: [
                Widget.Label({ label: icon, className: "tab-icon" }),
                Widget.Label({ label: label }),
            ],
        }),
    });
}

function Header() {
    return Widget.Box({
        className: "gamehub-header",
        children: [
            // Logo
            Widget.Box({
                className: "gamehub-logo",
                children: [
                    Widget.Label({ label: "🎮", className: "logo-icon" }),
                    Widget.Label({ label: "GameHub", className: "logo-text" }),
                ],
            }),

            // Spacer
            Widget.Box({ hexpand: true }),

            // GameMode indicator
            Widget.Box({
                className: gamehubState.bind().as((s) =>
                    `gamemode-indicator ${s.gamemodeActive ? "active" : ""}`
                ),
                children: [
                    Widget.Label({ label: "󱄄" }),
                    Widget.Label({
                        label: gamehubState.bind().as((s) =>
                            s.gamemodeActive ? "GameMode ON" : "GameMode OFF"
                        ),
                    }),
                ],
            }),

            // Scan button
            Widget.Button({
                className: "scan-btn",
                label: "󰑐 Scan",
                onClicked: scanGames,
            }),

            // Close button
            Widget.Button({
                className: "close-btn",
                label: "󰅖",
                onClicked: toggleGameHub,
            }),
        ],
    });
}

function SearchBar() {
    return Widget.Entry({
        className: "search-entry",
        placeholderText: "Search games...",
        text: gamehubState.bind().as((s) => s.searchQuery),
        onAccept: ({ text }) => searchGames(text),
        onChange: ({ text }) => {
            gamehubState.value = {
                ...gamehubState.value,
                searchQuery: text,
            };
            // Debounced search
            if (text.length >= 2) {
                Utils.timeout(300, () => {
                    if (gamehubState.value.searchQuery === text) {
                        searchGames(text);
                    }
                });
            }
        },
    });
}

function Tabs() {
    return Widget.Box({
        className: "gamehub-tabs",
        children: [
            TabButton("Recent", "󰋚", "recent"),
            TabButton("All", "󰊠", "all"),
            TabButton("Favorites", "󰋑", "favorites"),
            Widget.Separator({ className: "tab-separator" }),
            TabButton("Steam", "󰓓", "steam"),
            TabButton("Lutris", "󰺵", "lutris"),
            TabButton("Heroic", "󰊗", "heroic"),
        ],
    });
}

function Content() {
    return Widget.Stack({
        className: "gamehub-content",
        shown: gamehubState.bind().as((s) => {
            if (s.searchQuery.length >= 2) return "search";
            return s.activeTab;
        }),
        children: {
            recent: Widget.Box({
                vertical: true,
                children: [
                    Widget.Label({
                        className: "section-title",
                        label: "Recently Played",
                        xalign: 0,
                    }),
                    gamehubState.bind().as((s) =>
                        GameList(s.recentGames, "No recent games. Start playing!")
                    ),
                ],
            }),
            all: Widget.Box({
                vertical: true,
                child: gamehubState.bind().as((s) =>
                    GameList(s.games, "No games found. Click Scan to detect games.")
                ),
            }),
            favorites: Widget.Box({
                vertical: true,
                child: gamehubState.bind().as((s) =>
                    GameList(s.favorites, "No favorites yet. Right-click a game to add.")
                ),
            }),
            steam: Widget.Box({
                vertical: true,
                child: gamehubState.bind().as((s) =>
                    GameList(
                        s.games.filter((g) => g.source === "steam"),
                        "No Steam games found"
                    )
                ),
            }),
            lutris: Widget.Box({
                vertical: true,
                child: gamehubState.bind().as((s) =>
                    GameList(
                        s.games.filter((g) => g.source === "lutris"),
                        "No Lutris games found"
                    )
                ),
            }),
            heroic: Widget.Box({
                vertical: true,
                child: gamehubState.bind().as((s) =>
                    GameList(
                        s.games.filter((g) => g.source === "heroic"),
                        "No Heroic games found"
                    )
                ),
            }),
            search: Widget.Box({
                vertical: true,
                children: [
                    Widget.Label({
                        className: "section-title",
                        label: gamehubState.bind().as(
                            (s) => `Search results for "${s.searchQuery}"`
                        ),
                        xalign: 0,
                    }),
                    gamehubState.bind().as((s) =>
                        GameList(s.searchResults, "No games match your search")
                    ),
                ],
            }),
        },
    });
}

function StatusBar() {
    return Widget.Box({
        className: "gamehub-statusbar",
        children: [
            // Total games
            Widget.Label({
                className: "status-item",
                label: gamehubState.bind().as((s) =>
                    `${s.status?.total_games || 0} games`
                ),
            }),

            Widget.Separator({ className: "status-separator" }),

            // Sources status
            Widget.Label({
                className: "status-item",
                label: gamehubState.bind().as((s) => {
                    const sources = s.status?.sources_available || {};
                    const active = Object.entries(sources)
                        .filter(([_, v]) => v)
                        .map(([k]) => k);
                    return `Sources: ${active.join(", ") || "none"}`;
                }),
            }),

            Widget.Box({ hexpand: true }),

            // Loading indicator
            Widget.Label({
                className: "loading-indicator",
                label: "󰦖 Loading...",
                visible: gamehubState.bind().as((s) => s.loading),
            }),
        ],
    });
}

// ═══════════════════════════════════════════════════════════════════
// MAIN WINDOW
// ═══════════════════════════════════════════════════════════════════

export function GameHubWindow() {
    return Widget.Window({
        name: "purma-gamehub",
        className: "gamehub-window",
        anchor: ["top", "bottom", "left", "right"],
        exclusivity: "normal",
        layer: "overlay",
        keymode: "on-demand",
        visible: gamehubState.bind().as((s) => s.visible),
        setup: (self) => {
            self.keybind("Escape", () => {
                if (gamehubState.value.selectedGame) {
                    gamehubState.value = {
                        ...gamehubState.value,
                        selectedGame: null,
                    };
                } else {
                    toggleGameHub();
                }
            });
        },
        child: Widget.Box({
            className: "gamehub-container",
            vertical: true,
            children: [
                Header(),
                SearchBar(),
                Tabs(),
                Content(),
                StatusBar(),
            ],
        }),
    });
}

// ═══════════════════════════════════════════════════════════════════
// BAR BUTTON
// ═══════════════════════════════════════════════════════════════════

export function GameHubButton() {
    return Widget.Button({
        className: "bar-gamehub-btn",
        tooltipText: "GameHub (Super+G)",
        onClicked: toggleGameHub,
        child: Widget.Label({ label: "🎮" }),
    });
}

// ═══════════════════════════════════════════════════════════════════
// TOGGLE FUNCTION
// ═══════════════════════════════════════════════════════════════════

export function toggleGameHub() {
    const state = gamehubState.value;

    if (!state.visible) {
        // Opening - load data
        loadStatus();
        loadRecentGames();
        loadFavorites();
    }

    gamehubState.value = {
        ...state,
        visible: !state.visible,
    };
}

// Exportar para uso externo
globalThis.toggleGameHub = toggleGameHub;
