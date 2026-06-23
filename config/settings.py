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
COR_PATH: tuple[int, int, int] = (190, 50, 50)      # vermelho do caminho
COR_GRID: tuple[int, int, int] = (90, 90, 90)       # cinza das linhas do grid
COR_TEXTO: tuple[int, int, int] = (235, 235, 235)   # texto claro

# --- Economia / vida iniciais ---
INITIAL_COINS: int = 150
INITIAL_LIVES: int = 20

# --- Cartas e HUD ---
CARD_WIDTH: int = 150  # mais largo para caber stats/descrição
CARD_HEIGHT: int = 95
COLOR_GOLD: tuple[int, int, int] = (255, 200, 50)      # texto de moedas/custo
COLOR_HUD_BG: tuple[int, int, int] = (15, 15, 30)      # fundo da barra inferior
COLOR_CARD_BG: tuple[int, int, int] = (26, 26, 46)     # fundo das cartas
COLOR_SELECTED: tuple[int, int, int] = (255, 200, 50)  # borda da carta selecionada
COLOR_CARD_STATS: tuple[int, int, int] = (180, 180, 180)   # stats da carta
COLOR_CARD_DESC: tuple[int, int, int] = (120, 180, 255)    # descrição (azul claro)
COLOR_SLOT_ON: tuple[int, int, int] = (255, 200, 50)       # slot preenchido
COLOR_SLOT_OFF: tuple[int, int, int] = (60, 60, 80)        # slot vazio
COLOR_CARD_LIMIT: tuple[int, int, int] = (220, 60, 60)     # borda no limite
MAX_PER_TYPE: int = 4  # máximo de torres do mesmo tipo no campo

# --- Áudio ---
MUSIC_FADE_DURATION: float = 8.0   # segundos para o volume ir de 0 -> 1
KILLTHATBOY_DURATION: float = 1.0  # corte do killthatboy.mp3 (segundos)
