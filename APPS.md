# PurmaLinux - Gestión de Aplicaciones

Este documento describe cómo gestionar las aplicaciones que se instalan y preconfiguran en PurmaLinux.

## 📁 Estructura de Archivos

```
PurmaLinux/
├── base/packages/
│   ├── core.txt          # Paquetes esenciales del sistema
│   ├── ai.txt            # Dependencias del stack de IA
│   ├── desktop.txt       # Paquetes para versión Desktop (Openbox)
│   ├── i3.txt            # Paquetes para versión i3
│   └── apps.txt          # 🆕 Aplicaciones de usuario
│
└── base/configs/apps/    # 🆕 Configuraciones personalizadas
    ├── README.md
    ├── firefox/
    ├── neovim/
    └── [app-name]/
```

## 📝 Agregar Nuevas Aplicaciones

### Opción 1: Solo Instalación (sin configuración)

Edita `base/packages/apps.txt` y agrega la aplicación:

```bash
# Ejemplo: agregar Brave Browser
brave-browser [PPA]               # Navegador con privacidad
```

### Opción 2: Con Configuración Personalizada

1. **Agrega la aplicación en apps.txt con marca [CONFIG]:**

```bash
firefox [CONFIG]                  # Navegador principal
```

2. **Crea directorio de configuración:**

```bash
mkdir -p base/configs/apps/firefox
```

3. **Agrega archivos de configuración:**

```bash
# Ejemplo: user.js para Firefox
cat > base/configs/apps/firefox/user.js << 'EOF'
// PurmaLinux Firefox - Aurora Theme
user_pref("browser.theme.dark", true);
user_pref("privacy.trackingprotection.enabled", true);
EOF
```

4. **(Opcional) Script de instalación personalizado:**

```bash
cat > base/configs/apps/firefox/install.sh << 'EOF'
#!/bin/bash
# Script de instalación personalizado para Firefox
echo "Configurando Firefox..."
# Tus comandos aquí
EOF
chmod +x base/configs/apps/firefox/install.sh
```

## 🏷️ Marcadores en apps.txt

| Marcador | Significado | Ejemplo |
|----------|-------------|---------|
| `[CONFIG]` | Requiere configuración personalizada | `firefox [CONFIG]` |
| `[FLATPAK]` | Instalar vía Flatpak | `discord [FLATPAK]` |
| `[SNAP]` | Instalar vía Snap | `code [SNAP]` |
| `[PPA]` | Requiere PPA adicional | `brave-browser [PPA]` |
| `[AUR]` | Arch User Repository (futuro) | `yay [AUR]` |
| `[DEB]` | Paquete .deb externo | `zoom [DEB]` |

## 📦 Categorías de Aplicaciones

Las aplicaciones en `apps.txt` están organizadas en categorías:

- **Navegadores Web**: Firefox, Chromium, Brave
- **Editores de Código**: VS Code, Neovim, Vim
- **Desarrollo**: Docker, Git, GitHub CLI
- **Comunicación**: Slack, Discord, Telegram, Signal
- **Productividad**: LibreOffice, Obsidian, Notion
- **Media**: VLC, Spotify, GIMP, Blender, OBS
- **Utilidades**: Flameshot, Timeshift, GParted
- **Gaming**: Steam, Lutris, GameMode

## 🔧 Configuraciones Disponibles

Aplicaciones con configuración personalizada en `base/configs/apps/`:

- [ ] **Firefox** - Tema Aurora, privacidad, extensiones
- [ ] **Neovim** - Config básica con plugins
- [ ] **VS Code** - Settings y keybindings
- [ ] **Git** - Aliases y configuración global
- [ ] **Kitty** - Tema Aurora (ya en i3/kitty/)

## 🚀 Proceso de Instalación

El script `base/scripts/install-base.sh` debe:

1. Leer `apps.txt` línea por línea
2. Ignorar líneas comentadas con `#`
3. Detectar marcadores `[CONFIG]`, `[FLATPAK]`, etc.
4. Instalar paquetes según el método apropiado
5. Si tiene `[CONFIG]`, copiar configs desde `base/configs/apps/[app]/`
6. Ejecutar `install.sh` si existe
7. Aplicar permisos correctos

## 📋 Ejemplo Completo

### Agregar Obsidian con configuración

**1. En `base/packages/apps.txt`:**

```bash
obsidian [FLATPAK] [CONFIG]       # Notas markdown
```

**2. Crear configuración:**

```bash
mkdir -p base/configs/apps/obsidian
```

**3. Agregar configuración de tema:**

```bash
cat > base/configs/apps/obsidian/appearance.json << 'EOF'
{
  "theme": "obsidian",
  "cssTheme": "Aurora",
  "accentColor": "#00d4ff"
}
EOF
```

**4. Script de instalación:**

```bash
cat > base/configs/apps/obsidian/install.sh << 'EOF'
#!/bin/bash
# Instalar Obsidian vía Flatpak
flatpak install -y flathub md.obsidian.Obsidian

# Copiar configuración
mkdir -p ~/.config/obsidian
cp appearance.json ~/.config/obsidian/

echo "✓ Obsidian configurado con tema Aurora"
EOF
chmod +x base/configs/apps/obsidian/install.sh
```

## 🎨 Integración con Tema Aurora

Todas las configuraciones deben seguir el tema Aurora:

```css
/* Colores Aurora para aplicaciones */
--void:       #0a0e14;
--space:      #0d1117;
--nebula:     #161b22;
--cyan:       #00d4ff;  /* Acento principal */
--purple:     #a855f7;  /* Acento secundario */
--green:      #22c55e;
--yellow:     #f59e0b;
--red:        #ef4444;
```

## 📝 Checklist para Nuevas Apps

- [ ] Agregar en `apps.txt` con descripción clara
- [ ] Marcar con `[CONFIG]` si necesita configuración
- [ ] Crear directorio en `base/configs/apps/[app]/`
- [ ] Agregar archivos de configuración
- [ ] Crear `install.sh` si necesita pasos especiales
- [ ] Documentar en este archivo (APPS.md)
- [ ] Probar instalación en VM limpia
- [ ] Verificar tema Aurora aplicado correctamente

## 🔍 Verificación

Para verificar que una app está correctamente configurada:

```bash
# 1. Verificar que está en apps.txt
grep "nombre-app" base/packages/apps.txt

# 2. Si tiene [CONFIG], verificar directorio
ls -la base/configs/apps/nombre-app/

# 3. Probar instalación
sudo bash base/scripts/install-base.sh
```

## 💡 Tips

- **Mantén apps.txt organizado**: Usa las categorías existentes
- **Comenta por defecto**: Deja apps comentadas, el usuario las descomenta
- **Documenta dependencias**: Si una app necesita otra, documentarlo
- **Configs genéricas**: No incluir datos personales en las configs
- **Tema consistente**: Todas las apps deben usar colores Aurora

## 🎯 Roadmap

- [ ] Implementar parser de apps.txt en install-base.sh
- [ ] Agregar soporte para Flatpak/Snap
- [ ] Crear configs para apps más comunes
- [ ] Script para validar apps.txt
- [ ] Auto-detección de apps ya instaladas
- [ ] Menú interactivo para seleccionar apps
