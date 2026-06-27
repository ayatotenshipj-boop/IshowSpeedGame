"""Constantes globais do jogo Speed Vs Labubu.

Todas as constantes de configuração ficam aqui (resolução, FPS, grid, cores
e caminhos). Nada de lógica — apenas valores. Caminhos sempre via pathlib.
"""

import sys
from pathlib import Path

import pygame

# --- Diretórios (relativos à raiz do projeto, nunca absolutos hardcoded) ---
# Em execução normal: a raiz é o diretório-pai do pai de settings.py (config/).
# Empacotado com PyInstaller (--onefile): os dados são extraídos em sys._MEIPASS.
if getattr(sys, "frozen", False):
    RAIZ_PROJETO: Path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    RAIZ_PROJETO = Path(__file__).resolve().parent.parent
ASSETS_DIR: Path = RAIZ_PROJETO / "assets"
SOUNDS_DIR: Path = ASSETS_DIR / "sounds"   # música de fundo (sound.mp3)
AUDIO_DIR: Path = ASSETS_DIR / "audio"     # cues de habilidade (killthatboy, etc.)

# --- Janela ---
WINDOW_WIDTH: int = 1280
WINDOW_HEIGHT: int = 720
WINDOW_TITLE: str = "Speed Vs Labubu"
FPS: int = 60

# Resolução interna de renderização (a Surface onde tudo é desenhado, sempre
# 1280×720). A imagem é escalada para o tamanho real da janela/fullscreen com
# letterbox. Toda a UI continua referindo WINDOW_WIDTH/HEIGHT (= render space).
RENDER_WIDTH: int = WINDOW_WIDTH
RENDER_HEIGHT: int = WINDOW_HEIGHT

# --- Grid ---
CELL_SIZE: int = 64  # tamanho de cada célula do grid, em pixels

# Raio de hitbox/colisão das torres no posicionamento livre por pixel.
# Duas torres não podem ficar a menos de 2*HIT_RADIUS de distância (centro a
# centro). 0.4 da célula => diâmetro de bloqueio ~0.8 célula entre torres.
HIT_RADIUS: float = CELL_SIZE * 0.4

# --- Recorte (zoom) do mapa ---
# Frações da imagem original mantidas no recorte (foco no campo verde, sem
# arquibancadas). game_map usa para recortar; placement_grid usa para
# recalcular os waypoints proporcionalmente (path nunca hardcoded em pixels).
CROP_LEFT: float = 0.22
CROP_RIGHT: float = 0.78
CROP_TOP: float = 0.20
CROP_BOTTOM: float = 0.80

# --- Áreas da tela ---
# Área do mapa jogável (parte de cima) e barra inferior do HUD (cartas + stats).
MAP_RECT: pygame.Rect = pygame.Rect(0, 0, 1280, 620)
HUD_RECT: pygame.Rect = pygame.Rect(0, 620, 1280, 100)

# --- Paleta de cores base (RGB) ---
COR_FUNDO: tuple[int, int, int] = (20, 20, 28)      # fundo neutro escuro
COR_CAMPO: tuple[int, int, int] = (46, 138, 62)     # verde campo
COR_PATH: tuple[int, int, int] = (122, 16, 16)      # vermelho do caminho — --vermelho-path #7a1010
COR_GRID: tuple[int, int, int] = (90, 90, 90)       # cinza das linhas do grid
COR_TEXTO: tuple[int, int, int] = (240, 240, 232)   # texto claro — --branco #f0f0e8

# --- Economia / vida iniciais ---
INITIAL_COINS: int = 400  # v1.2.1: economia rebalanceada (era 150)
INITIAL_LIVES: int = 10   # padrão do modo "normal"; cada modo redefine (Bloco 5)

# --- Modos de dificuldade (v1.2.1) ---
# Multiplicadores aplicados na criação de cada inimigo (WaveManager) e vidas
# iniciais por modo. `hp_mult`/`speed_mult` afetam todos os inimigos (inclusive
# o boss); `reward_mult` escala as recompensas. O multiplicador de HP por wave
# (1-based) continua separado e o boss segue fora da escala de wave.
MODOS_DIFICULDADE: dict[str, dict] = {
    "facil": {
        "nome": "Fácil",
        "hp_mult": 0.7,      # Labubus com 70% do HP
        "speed_mult": 0.8,   # 20% mais lentos
        "reward_mult": 1.3,  # 30% mais moedas
        "lives": 15,         # mais vidas
        "descricao": "Para quem está conhecendo o jogo",
    },
    "normal": {
        "nome": "Normal",
        "hp_mult": 1.0,
        "speed_mult": 1.0,
        "reward_mult": 1.0,
        "lives": 10,
        "descricao": "A experiência balanceada",
    },
    "dificil": {
        "nome": "Difícil",
        "hp_mult": 1.5,      # Labubus com 150% do HP
        "speed_mult": 1.2,   # 20% mais rápidos
        "reward_mult": 0.8,  # 20% menos moedas
        "lives": 6,          # poucas vidas
        "descricao": "Para quem domina o jogo",
    },
}

# --- Cartas e HUD ---
CARD_WIDTH: int = 150  # mais largo para caber stats/descrição
CARD_HEIGHT: int = 95
COLOR_GOLD: tuple[int, int, int] = (255, 208, 64)          # --dourado #ffd040
COLOR_HUD_BG: tuple[int, int, int] = (15, 15, 30)          # legado — substituído por COR_FUNDO_HUD
COLOR_CARD_BG: tuple[int, int, int] = (17, 17, 8)          # --card-bg #111108 (era azul, agora oliva)
COLOR_SELECTED: tuple[int, int, int] = (255, 208, 64)       # borda da carta selecionada
COLOR_CARD_STATS: tuple[int, int, int] = (102, 102, 102)   # #666 — stats em cinza médio
COLOR_CARD_DESC: tuple[int, int, int] = (74, 158, 255)     # #4a9eff — descrição azul
COLOR_SLOT_ON: tuple[int, int, int] = (255, 208, 64)        # slot preenchido — --dourado
COLOR_SLOT_OFF: tuple[int, int, int] = (34, 34, 34)         # #222 — slot vazio
COLOR_CARD_LIMIT: tuple[int, int, int] = (220, 60, 60)      # borda no limite de torres
MAX_PER_TYPE: int = 4  # máximo de torres do mesmo tipo no campo

# --- Áudio ---
MUSIC_FADE_DURATION: float = 8.0   # segundos para o volume ir de 0 -> 1
KILLTHATBOY_DURATION: float = 1.0  # corte do killthatboy.mp3 (segundos)

# --- Fontes customizadas ---
FONTS_DIR: Path = ASSETS_DIR / "fonts"
FONTE_TITULO_PATH: Path = FONTS_DIR / "BebasNeue.ttf"

# ═══════════════════════════════════════════
# PALETA VISUAL — Speed Vs Labubu Remake
# Toda cor usada na UI deve vir daqui.
# ═══════════════════════════════════════════

# Campo
COR_CAMPO_BASE        = (30, 64, 16)    # --verde-campo #1e4010
COR_VERDE_CLARO       = (46, 96, 24)    # --verde-claro #2e6018
COR_CAMPO_LINHA       = (255, 255, 255)

# Labels dim (HUD, modais) — equivalente ao #555 do HTML
COR_LABEL_HUD         = (85, 85, 85)

# Cinzas neutros (--cinza-escuro/medio/claro)
COR_CINZA_ESCURO      = (14, 14, 14)     # --cinza-escuro #0e0e0e
COR_CINZA_MEDIO       = (24, 24, 24)     # --cinza-medio  #181818
COR_CINZA_CLARO       = (37, 37, 37)     # --cinza-claro  #252525

# Fundo das UIs
COR_FUNDO_TELA        = (14, 14, 14)     # --cinza-escuro #0e0e0e
COR_FUNDO_HUD         = (12, 20, 8)      # tom esverdeado — remete ao campo (escolha do usuário)
COR_FUNDO_CARTA       = (17, 17, 8)      # --card-bg #111108
COR_FUNDO_MODAL       = (17, 17, 8)      # --card-bg #111108 (mesmo tom para modais)

# Bordas
COR_BORDA_CARTA       = (42, 42, 24)     # --card-border #2a2a18
COR_BORDA_ATIVA       = (255, 208, 64)   # dourado — carta selecionada
COR_BORDA_BUFF        = (255, 140, 0)    # laranja — Speed5 buff ativo
COR_BORDA_SUTIL       = (37, 34, 0)
COR_BORDA_MODAL       = (37, 40, 0)
COR_BORDA_MODAL_TOPO  = (255, 208, 64)  # 3px dourado no topo dos painéis

# Texto
COR_TEXTO_PRIMARIO    = (240, 240, 232)
COR_TEXTO_SECUNDARIO  = (100, 100, 64)
COR_TEXTO_DESATIVO    = (50, 50, 32)
COR_TEXTO_LABEL       = (68, 68, 48)

# Acentos
COR_DOURADO           = (255, 208, 64)
COR_DOURADO_ESCURO    = (184, 120, 0)
COR_VERDE_NEON        = (127, 255, 58)
COR_CIANO             = (0, 255, 204)
COR_VERMELHO          = (212, 43, 30)
COR_LARANJA           = (255, 140, 0)
COR_ROXO              = (192, 80, 255)
COR_AZUL              = (74, 176, 255)

# Overlay de posicionamento
COR_OVERLAY_LIVRE     = (50, 200, 50)   # verde — área livre
COR_OVERLAY_PATH      = (200, 40, 40)   # vermelho — caminho dos inimigos
COR_OVERLAY_INVALIDO  = (220, 50, 50)   # vermelho — hover inválido / range bloqueada
COR_OVERLAY_VALIDO    = (50, 220, 80)   # verde — hover válido / range livre

# Alphas padrão (int 0-255)
ALPHA_OVERLAY_GLOBAL  = 55    # overlay sobre o campo inteiro ao selecionar carta
ALPHA_OVERLAY_HOVER   = 90    # highlight da célula sob o cursor
ALPHA_MODAL_BG        = 200   # fundo escuro sob modais
ALPHA_PATH_VISIVEL    = 160   # path quando carta selecionada

# HUD — barra superior e botões
COR_BARRA_HUD_TOPO   = (10, 10, 20, 170)   # legado (não usado)
COR_HUD_BARRA_BG     = (5, 5, 5)           # fundo da barra de HUD topo (#050505)
COR_HUD_BORDA        = (26, 24, 0)         # borda barra e botões HUD (#1a1800)
COR_BTN_HUD_TEXTO    = (100, 100, 64)      # texto inativo dos botões HUD (#666640)
COR_BTN_HUD_HOVER_BG = (26, 24, 0)        # bg do botão HUD em hover (#1a1800)
COR_BTN_HUD_ATIVO_TX = (10, 8, 0)         # texto escuro no botão HUD ativo
COR_VIDA_OK          = (80, 220, 90)        # vidas > 6
COR_VIDA_ALERTA      = (240, 210, 60)       # vidas 3-6
COR_VIDA_CRITICA     = (220, 60, 60)        # vidas < 3
COR_BTN_FUNDO        = (30, 30, 45)        # legado
COR_BTN_INATIVO      = (120, 120, 130)     # legado
COR_BTN_TEXTO_INATIVO = (180, 180, 190)    # legado
COR_BTN_ATIVO        = (90, 220, 110)      # legado
COR_BTN_TEXTO_ATIVO  = (170, 255, 190)     # legado
COR_BTN_SPEED_ESCURO = (150, 120, 30)      # legado
COR_SKIP_FUNDO       = (40, 90, 50)        # legado
COR_SKIP_BORDA       = (90, 220, 110)      # legado
COR_SKIP_TEXTO       = (220, 255, 220)     # legado
COR_BOSS_ALERTA      = (230, 50, 50)       # texto piscante de boss

# Cartas
COR_CARTA_TOPO       = (58, 58, 24)        # #3a3a18 — borda-topo da carta (era azul)
COR_OVERLAY_BLOQUEADA = (0, 0, 0, 140)    # overlay escuro — carta inacessível
COR_TOOLTIP_FUNDO    = (18, 18, 32, 240)  # fundo semi-transparente do tooltip
COR_BUFF_IND         = (255, 230, 60)     # indicador [B] de buff ativo
COR_SKILL_USADA      = (120, 120, 120)    # indicador [USADA] de habilidade gasta
COR_ROXO_IND         = (180, 90, 220)     # indicador [SKILL] disponível

# Menus / modais
COR_OVERLAY_MODAL    = (0, 0, 0, 180)    # overlay escuro padrão sobre telas
COR_OVERLAY_BG_MENU  = (0, 0, 0, 150)   # escurecimento do mapa no menu
COR_OVERLAY_PAUSE    = (10, 10, 20, 180) # overlay do pause (azul-escuro)
COR_SLIDER_TRACK     = (60, 60, 70)     # trilha do slider de volume
COR_SLIDER_HANDLE    = (40, 40, 50)     # interior do handle do slider
COR_GAMEOVER_TITULO  = (212, 43, 30)    # --vermelho #d42b1e — título vermelho no game over
COR_VICTORY_TITULO   = (255, 208, 64)   # --dourado #ffd040 — título dourado na vitória (HTML)
COR_BANNER_FUNDO     = (35, 30, 10, 235) # banner de conquista desbloqueada
COR_BANNER_DESC      = (200, 200, 210)  # texto de descrição no banner

# Intro (cena de diálogo)
COR_INTRO_ESCURO     = (0, 0, 0, 160)  # overlay sobre o mapa na intro
COR_DIALOGO_FUNDO    = (20, 20, 20)    # fundo da caixa de diálogo
COR_HINT_DIALOGO     = (150, 150, 150) # texto de dica na intro

# Efeito especial (Speed7 grayscale)
COR_MAP_GRAYSCALE    = (128, 128, 128, 120) # overlay cinza sobre o mapa
COR_SETA_PATH        = (245, 245, 245, 200) # setas brancas animadas no path
COR_DEBUG_OCUPADO    = (40, 90, 220, 120)   # célula OCCUPIED no modo dev

# Leaderboard e conquistas
COR_PRATA            = (192, 192, 192)     # posição 2 no leaderboard
COR_BRONZE           = (205, 127, 50)      # posição 3 no leaderboard
COR_MEDALHA_LENDA    = (200, 80, 200)      # conquista difícil (roxo lenda)
COR_BLOQUEADA        = (90, 90, 100)       # conquista bloqueada
COR_OVERLAY_LB       = (0, 0, 0, 190)     # overlay do painel de leaderboard
