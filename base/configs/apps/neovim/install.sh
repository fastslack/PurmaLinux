#!/bin/bash
# PurmaLinux - Neovim Installation and Configuration

set -e

echo "Configurando Neovim con tema Aurora..."

# Crear directorio de configuración
mkdir -p "$HOME/.config/nvim"

# Copiar init.vim
cp init.vim "$HOME/.config/nvim/init.vim"

echo "✓ Configuración copiada a ~/.config/nvim/init.vim"

# Instalar vim-plug si no existe
if [ ! -f "$HOME/.local/share/nvim/site/autoload/plug.vim" ]; then
    echo "Instalando vim-plug..."
    curl -fLo "$HOME/.local/share/nvim/site/autoload/plug.vim" --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
    echo "✓ vim-plug instalado"
fi

# Instalar plugins
echo "Instalando plugins de Neovim..."
nvim --headless +PlugInstall +qall 2>/dev/null || true

echo "✓ Neovim configurado con tema Aurora"
echo "  Ejecuta 'nvim' para empezar a usar"
