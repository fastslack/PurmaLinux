# Configuraciones de Aplicaciones

Este directorio contiene las configuraciones personalizadas para las aplicaciones instaladas en PurmaLinux.

## Estructura

```
configs/apps/
├── README.md                    # Este archivo
├── firefox/                     # Configuración de Firefox
│   ├── user.js                  # Preferencias de usuario
│   └── userChrome.css           # Personalización UI
├── vscode/                      # Configuración de VS Code
│   ├── settings.json
│   └── keybindings.json
├── neovim/                      # Configuración de Neovim
│   └── init.vim
└── [app-name]/                  # Otras aplicaciones
    └── config files
```

## Cómo Agregar Configuraciones

### 1. Crear directorio para la aplicación

```bash
mkdir -p base/configs/apps/nombre-app
```

### 2. Agregar archivos de configuración

Coloca los archivos de configuración que quieres que se instalen por defecto.

### 3. Crear script de instalación (opcional)

Si la aplicación requiere pasos adicionales, crea un script:

```bash
base/configs/apps/nombre-app/install.sh
```

### 4. Marcar en apps.txt

En `base/packages/apps.txt`, marca la aplicación con `[CONFIG]`:

```
nombre-app [CONFIG]              # Descripción
```

## Aplicaciones con Configuración

Las siguientes aplicaciones tienen configuraciones personalizadas:

- **Firefox**: Tema Aurora, privacidad mejorada, extensiones preinstaladas
- **Neovim**: Configuración básica con plugins esenciales
- **Git**: Aliases y configuración global
- **Kitty**: Tema Aurora integrado (ya en i3/kitty/)

## Instalación Automática

El script `base/scripts/install-base.sh` debe:

1. Leer `apps.txt` y detectar aplicaciones con `[CONFIG]`
2. Copiar configuraciones desde `configs/apps/[app]/` a la ubicación correcta
3. Ejecutar `install.sh` si existe
4. Aplicar permisos correctos

## Ejemplo: Agregar Firefox

```bash
# 1. Crear directorio
mkdir -p base/configs/apps/firefox

# 2. Agregar user.js
cat > base/configs/apps/firefox/user.js << 'EOF'
// PurmaLinux Firefox Config
user_pref("browser.theme.dark", true);
user_pref("privacy.trackingprotection.enabled", true);
EOF

# 3. Marcar en apps.txt
echo "firefox [CONFIG]              # Navegador principal" >> base/packages/apps.txt
```

## Ubicaciones de Configuración

Ubicaciones comunes donde se copian las configs:

- `~/.config/[app]/` - Mayoría de aplicaciones modernas
- `~/.local/share/[app]/` - Datos de aplicación
- `~/.[app]rc` - Configuraciones legacy
- `~/.mozilla/firefox/` - Firefox
- `~/.vscode/` o `~/.config/Code/` - VS Code

## Notas

- Las configuraciones deben ser **genéricas** y funcionar en cualquier instalación
- No incluir datos personales (tokens, passwords, etc.)
- Documentar cualquier configuración no obvia
- Mantener compatibilidad con el tema Aurora
