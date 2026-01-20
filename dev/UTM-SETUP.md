# PurmaLinux - Guía de Setup en UTM

Guía paso a paso para configurar el entorno de desarrollo de PurmaLinux usando UTM en macOS con Apple Silicon.

## Requisitos

- macOS con Apple Silicon (M1/M2/M3/M4)
- 16GB RAM mínimo (8GB asignados a la VM)
- 60GB espacio libre en disco
- UTM instalado

## Paso 1: Instalar UTM

```bash
brew install --cask utm
```

O descargar desde: https://mac.getutm.app/

## Paso 2: Descargar Ubuntu Server ARM64

1. Ir a: https://ubuntu.com/download/server/arm
2. Descargar **Ubuntu Server 24.04.x LTS** para ARM
3. El archivo será algo como: `ubuntu-24.04-live-server-arm64.iso`

## Paso 3: Crear la Máquina Virtual

### 3.1 Abrir UTM y crear nueva VM

1. Abrir UTM
2. Click en **"Create a New Virtual Machine"**
3. Seleccionar **"Virtualize"** (NO Emulate - queremos rendimiento nativo ARM)

### 3.2 Configurar sistema operativo

1. Seleccionar **"Linux"**
2. Click en **"Browse"** y seleccionar el ISO de Ubuntu Server ARM64
3. Click **"Continue"**

### 3.3 Configurar hardware

| Opción | Valor Recomendado |
|--------|-------------------|
| Memory | **8192 MB** (8GB) |
| CPU Cores | **4** |

Click **"Continue"**

### 3.4 Configurar almacenamiento

| Opción | Valor |
|--------|-------|
| Storage Size | **64 GB** |

Click **"Continue"**

### 3.5 Carpeta compartida (opcional pero recomendado)

1. Enable **"Enable Directory Sharing"**
2. Click **"Browse"** y seleccionar tu carpeta de proyecto:
   ```
   /Users/fastslack/mtwProjects/LABS/PurmaLinux
   ```

Click **"Continue"**

### 3.6 Resumen

1. Cambiar nombre a: **"PurmaLinux-Dev"**
2. Click **"Save"**

## Paso 4: Instalar Ubuntu Server

### 4.1 Iniciar la VM

1. Seleccionar la VM "PurmaLinux-Dev"
2. Click en el botón **Play** (▶)

### 4.2 Instalación de Ubuntu

1. Seleccionar idioma: **Español** o **English**
2. Seleccionar **"Ubuntu Server"** (NO minimizado)
3. Configurar red: **Usar DHCP** (default)
4. Proxy: **Dejar vacío**
5. Mirror: **Usar default**
6. Almacenamiento: **"Use an entire disk"** → Continuar
7. Confirmar: **"Continue"**

### 4.3 Configurar usuario

| Campo | Valor Sugerido |
|-------|----------------|
| Your name | Tu nombre |
| Server name | `purmalinux` |
| Username | `purma` |
| Password | (tu contraseña) |

### 4.4 SSH y paquetes

1. **Install OpenSSH server**: ✓ Sí
2. Featured Server Snaps: **No seleccionar ninguno**

### 4.5 Esperar instalación

La instalación tardará unos minutos. Cuando termine:
1. Click **"Reboot Now"**
2. Cuando pida remover el medio de instalación, presiona **Enter**

## Paso 5: Configuración Post-Instalación

### 5.1 Login en la VM

```
purmalinux login: purma
Password: (tu contraseña)
```

### 5.2 Ejecutar script de setup

**Opción A: Desde el repo (si tienes carpeta compartida)**

```bash
# Montar carpeta compartida
sudo mkdir -p /mnt/shared
sudo mount -t 9p -o trans=virtio share /mnt/shared -oversion=9p2000.L

# Ejecutar script
bash /mnt/shared/dev/vm-post-install.sh
```

**Opción B: Clonar y ejecutar**

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/PurmaLinux.git ~/PurmaLinux

# Ejecutar script
bash ~/PurmaLinux/dev/vm-post-install.sh
```

**Opción C: Copiar manualmente vía SCP desde tu Mac**

```bash
# En tu Mac (nueva terminal):
# Primero obtener IP de la VM (en la VM ejecutar: ip addr)
scp -r /Users/fastslack/mtwProjects/LABS/PurmaLinux purma@<IP_VM>:~/PurmaLinux

# Luego en la VM:
bash ~/PurmaLinux/dev/vm-post-install.sh
```

## Paso 6: Verificar instalación

```bash
# Verificar Ollama
ollama list

# Probar servidor Purma
purma-dev server &

# En otra terminal, probar API
curl http://localhost:11435/status
```

## Paso 7: Iniciar entorno gráfico

```bash
# Iniciar LightDM (login gráfico)
sudo systemctl start lightdm
```

Seleccionar sesión **Openbox** o **i3** en el menú de LightDM.

## Configuración de Red para Acceso desde Mac

### Obtener IP de la VM

En la VM:
```bash
ip addr show enp0s1 | grep inet
# Resultado ejemplo: inet 192.168.64.4/24
```

### Acceder desde tu Mac

```bash
# SSH
ssh purma@192.168.64.4

# API del servidor Purma
curl http://192.168.64.4:11435/status

# Montar carpeta vía SSHFS (opcional)
brew install sshfs
mkdir -p ~/mnt/purmalinux
sshfs purma@192.168.64.4:/home/purma/PurmaLinux ~/mnt/purmalinux
```

## Tips de Desarrollo

### Sincronizar código automáticamente

Usar la carpeta compartida de UTM o rsync:

```bash
# En tu Mac, sincronizar cambios
rsync -avz --exclude='venv' --exclude='__pycache__' \
    /Users/fastslack/mtwProjects/LABS/PurmaLinux/ \
    purma@192.168.64.4:~/PurmaLinux/
```

### Crear alias útiles

En tu Mac (`~/.zshrc`):
```bash
alias purma-vm="ssh purma@192.168.64.4"
alias purma-sync="rsync -avz --exclude='venv' --exclude='__pycache__' /Users/fastslack/mtwProjects/LABS/PurmaLinux/ purma@192.168.64.4:~/PurmaLinux/"
```

### Acceso VNC/Pantalla (opcional)

Si quieres ver la GUI desde tu Mac sin usar la ventana de UTM:

```bash
# En la VM
sudo apt install tigervnc-standalone-server
vncserver :1 -geometry 1920x1080

# En tu Mac
open vnc://192.168.64.4:5901
```

## Snapshots

UTM soporta snapshots. Recomiendo crear uno después de:
1. Instalación base de Ubuntu
2. Post-instalación completa
3. Antes de hacer cambios grandes

Para crear snapshot: UTM → Click derecho en VM → **"Clone..."** o usar el menú de snapshots.

## Troubleshooting

### La VM no arranca después de instalar
- Verificar que el ISO fue "eyectado" en la configuración de UTM
- En UTM: Edit VM → Drives → Eliminar el CD/DVD drive o cambiar a vacío

### No hay red en la VM
```bash
sudo dhclient enp0s1
```

### AGS no funciona
```bash
# Verificar que X11 está corriendo
echo $DISPLAY  # Debe mostrar :0 o similar

# Reiniciar AGS
ags -q && ags
```

### Ollama muy lento
- Verificar que estás usando ARM64 nativo, no emulación x86
- Asignar más RAM a la VM (12GB si tienes 32GB en el host)
