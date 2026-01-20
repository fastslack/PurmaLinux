" PurmaLinux - Neovim Configuration
" Configuración básica con tema Aurora

" ═══════════════════════════════════════════════════════════════════════════════
"  General Settings
" ═══════════════════════════════════════════════════════════════════════════════
set number                      " Números de línea
set relativenumber              " Números relativos
set mouse=a                     " Soporte de mouse
set clipboard=unnamedplus       " Clipboard del sistema
set expandtab                   " Espacios en lugar de tabs
set tabstop=4                   " Tab = 4 espacios
set shiftwidth=4                " Indent = 4 espacios
set smartindent                 " Auto-indent inteligente
set wrap                        " Wrap de líneas
set ignorecase                  " Búsqueda case-insensitive
set smartcase                   " Case-sensitive si hay mayúsculas
set incsearch                   " Búsqueda incremental
set hlsearch                    " Highlight búsquedas
set termguicolors               " True colors
set cursorline                  " Highlight línea actual
set signcolumn=yes              " Columna de signos siempre visible
set updatetime=300              " Faster completion
set timeoutlen=500              " Faster key sequences

" ═══════════════════════════════════════════════════════════════════════════════
"  Aurora Color Scheme (básico)
" ═══════════════════════════════════════════════════════════════════════════════
syntax enable
set background=dark

" Colores Aurora básicos
highlight Normal guibg=#0d1117 guifg=#c9d1d9
highlight CursorLine guibg=#161b22
highlight LineNr guifg=#8b949e
highlight CursorLineNr guifg=#00d4ff
highlight Comment guifg=#8b949e gui=italic
highlight String guifg=#22c55e
highlight Function guifg=#00d4ff
highlight Keyword guifg=#a855f7
highlight Type guifg=#f59e0b
highlight Constant guifg=#ec4899

" ═══════════════════════════════════════════════════════════════════════════════
"  Key Mappings
" ═══════════════════════════════════════════════════════════════════════════════
let mapleader = " "             " Space como leader

" Navegación entre ventanas
nnoremap <C-h> <C-w>h
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-l> <C-w>l

" Guardar y salir
nnoremap <leader>w :w<CR>
nnoremap <leader>q :q<CR>
nnoremap <leader>x :x<CR>

" Limpiar highlight de búsqueda
nnoremap <leader>h :nohlsearch<CR>

" ═══════════════════════════════════════════════════════════════════════════════
"  Plugin Manager (vim-plug)
" ═══════════════════════════════════════════════════════════════════════════════
" Auto-install vim-plug si no existe
let data_dir = has('nvim') ? stdpath('data') . '/site' : '~/.vim'
if empty(glob(data_dir . '/autoload/plug.vim'))
  silent execute '!curl -fLo '.data_dir.'/autoload/plug.vim --create-dirs  https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'
  autocmd VimEnter * PlugInstall --sync | source $MYVIMRC
endif

" Plugins
call plug#begin()

" Esenciales
Plug 'tpope/vim-sensible'           " Defaults sensatos
Plug 'tpope/vim-surround'           " Manipular pares
Plug 'tpope/vim-commentary'         " Comentarios fáciles
Plug 'jiangmiao/auto-pairs'         " Auto-cerrar pares

" File explorer
Plug 'preservim/nerdtree'

" Fuzzy finder
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'

" Status line
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'

" Git integration
Plug 'tpope/vim-fugitive'

call plug#end()

" ═══════════════════════════════════════════════════════════════════════════════
"  Plugin Configuration
" ═══════════════════════════════════════════════════════════════════════════════

" NERDTree
nnoremap <leader>e :NERDTreeToggle<CR>
let NERDTreeShowHidden=1

" FZF
nnoremap <leader>f :Files<CR>
nnoremap <leader>b :Buffers<CR>
nnoremap <leader>/ :Rg<CR>

" Airline
let g:airline_theme='dark'
let g:airline_powerline_fonts=1
let g:airline#extensions#tabline#enabled=1
