// PurmaLinux - Firefox Configuration
// Tema Aurora y configuraciones de privacidad

// ═══════════════════════════════════════════════════════════════════════════════
//  Tema y Apariencia
// ═══════════════════════════════════════════════════════════════════════════════
user_pref("browser.theme.dark-private-windows", true);
user_pref("browser.theme.toolbar-theme", 0); // Dark theme
user_pref("ui.systemUsesDarkTheme", 1);

// ═══════════════════════════════════════════════════════════════════════════════
//  Privacidad
// ═══════════════════════════════════════════════════════════════════════════════
user_pref("privacy.trackingprotection.enabled", true);
user_pref("privacy.trackingprotection.socialtracking.enabled", true);
user_pref("privacy.donottrackheader.enabled", true);
user_pref("privacy.resistFingerprinting", false); // Puede romper algunos sitios
user_pref("privacy.clearOnShutdown.cache", false);
user_pref("privacy.clearOnShutdown.cookies", false);
user_pref("privacy.clearOnShutdown.history", false);

// ═══════════════════════════════════════════════════════════════════════════════
//  Performance
// ═══════════════════════════════════════════════════════════════════════════════
user_pref("browser.cache.disk.enable", true);
user_pref("browser.cache.memory.enable", true);
user_pref("browser.sessionhistory.max_total_viewers", 4);
user_pref("network.http.pipelining", true);

// ═══════════════════════════════════════════════════════════════════════════════
//  UX Improvements
// ═══════════════════════════════════════════════════════════════════════════════
user_pref("browser.download.useDownloadDir", true);
user_pref("browser.tabs.closeWindowWithLastTab", false);
user_pref("browser.urlbar.suggest.searches", true);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);

// ═══════════════════════════════════════════════════════════════════════════════
//  Developer Tools
// ═══════════════════════════════════════════════════════════════════════════════
user_pref("devtools.theme", "dark");
user_pref("devtools.toolbox.host", "bottom");
