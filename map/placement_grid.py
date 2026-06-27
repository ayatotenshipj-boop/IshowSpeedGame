"""Grid de posicionamento de torres.

Divide a área do mapa (`MAP_RECT`) em células de `CELL_SIZE`×`CELL_SIZE`.
Cada célula tem um estado: FREE (livre), PATH (caminho dos inimigos, bloqueada)
ou OCCUPIED (torre posicionada). As células PATH são derivadas dos waypoints
em `config/path.json`, interpolando ortogonalmente entre pontos consecutivos.
"""

import json
import math
from pathlib import Path

import pygame

from config.settings import (
    CELL_SIZE,
    COR_GRID,
    COR_PATH,
    CROP_BOTTOM,
    CROP_LEFT,
    CROP_RIGHT,
    CROP_TOP,
    MAP_RECT,
    RAIZ_PROJETO,
    COR_SETA_PATH,
    COR_DEBUG_OCUPADO,
)

# Estados possíveis de uma célula.
FREE = "FREE"
PATH = "PATH"
OCCUPIED = "OCCUPIED"

# Caminho do arquivo de waypoints (sempre via pathlib).
PATH_JSON: Path = RAIZ_PROJETO / "config" / "path.json"


class PlacementGrid:
    """Controla os estados das células do grid sobre o mapa."""

    def __init__(self, path_json: Path = PATH_JSON) -> None:
        # Número de colunas/linhas que cabem na área do mapa.
        self.cols: int = MAP_RECT.width // CELL_SIZE
        self.rows: int = MAP_RECT.height // CELL_SIZE

        # Matriz de estados [linha][coluna], todas começam livres.
        self._celulas: list[list[str]] = [
            [FREE for _ in range(self.cols)] for _ in range(self.rows)
        ]

        # Waypoints recalculados pelo recorte do mapa (preenchidos em
        # _marcar_path). `waypoints` (dicts) é a fonte pública usada pelos
        # inimigos; `_waypoints_px` (tuplas) é usado pelo draw_path.
        self.waypoints: list[dict] = []
        self._waypoints_px: list[tuple[int, int]] = []

        self._marcar_path(path_json)

    # ------------------------------------------------------------------ #
    # Construção do path
    # ------------------------------------------------------------------ #
    def _marcar_path(self, path_json: Path) -> None:
        """Lê os waypoints e marca como PATH as células entre eles."""
        if not path_json.is_file():
            raise FileNotFoundError(f"Arquivo de path não encontrado: {path_json}")

        dados = json.loads(path_json.read_text(encoding="utf-8"))
        brutos = dados["waypoints"]

        # Recalcula cada waypoint pelo recorte do mapa (proporcional às frações
        # CROP_*). Os valores no JSON são frações de MAP_RECT do mapa completo;
        # após o recorte, mapeiam para novas posições de tela.
        self.waypoints = [self._transformar(p["x"], p["y"]) for p in brutos]

        # Guarda os waypoints em pixels de tela (para o draw_path).
        self._waypoints_px = [(p["x"], p["y"]) for p in self.waypoints]

        # Converte cada waypoint (já transformado) em coordenada de célula.
        celulas_wp = [
            self._pixel_para_celula(p["x"], p["y"]) for p in self.waypoints
        ]

        # Interpola célula-a-célula entre waypoints consecutivos (ortogonal).
        for (cx0, cy0), (cx1, cy1) in zip(celulas_wp, celulas_wp[1:]):
            self._marcar_linha(cx0, cy0, cx1, cy1)

    def _marcar_linha(self, cx0: int, cy0: int, cx1: int, cy1: int) -> None:
        """Marca como PATH todas as células no segmento reto entre dois pontos."""
        passo_x = (cx1 > cx0) - (cx1 < cx0)  # sinal: -1, 0 ou 1
        passo_y = (cy1 > cy0) - (cy1 < cy0)
        cx, cy = cx0, cy0
        self._set_path(cx, cy)
        while (cx, cy) != (cx1, cy1):
            cx += passo_x
            cy += passo_y
            self._set_path(cx, cy)

    def _set_path(self, cx: int, cy: int) -> None:
        """Marca uma célula como PATH se estiver dentro do grid."""
        if 0 <= cy < self.rows and 0 <= cx < self.cols:
            self._celulas[cy][cx] = PATH

    # ------------------------------------------------------------------ #
    # Conversões e consultas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _transformar(x: float, y: float) -> dict:
        """Mapeia um waypoint do mapa completo para a tela após o recorte CROP_*.

        `x`/`y` estão no espaço de MAP_RECT do mapa inteiro. Converte para
        fração, reposiciona dentro da janela de recorte e reescala para
        MAP_RECT — mantendo o caminho alinhado ao campo ampliado.
        """
        fx = (x - MAP_RECT.x) / MAP_RECT.width
        fy = (y - MAP_RECT.y) / MAP_RECT.height
        nx = (fx - CROP_LEFT) / (CROP_RIGHT - CROP_LEFT)
        ny = (fy - CROP_TOP) / (CROP_BOTTOM - CROP_TOP)
        return {
            "x": int(MAP_RECT.x + nx * MAP_RECT.width),
            "y": int(MAP_RECT.y + ny * MAP_RECT.height),
        }

    def _pixel_para_celula(self, px: int, py: int) -> tuple[int, int]:
        """Converte pixels (relativos à janela) em (coluna, linha) do grid."""
        cx = (px - MAP_RECT.x) // CELL_SIZE
        cy = (py - MAP_RECT.y) // CELL_SIZE
        return cx, cy

    def pixel_to_cell(self, pixel_x: int, pixel_y: int) -> tuple[int, int]:
        """Converte pixels da janela em (coluna, linha) do grid (público)."""
        return self._pixel_para_celula(pixel_x, pixel_y)

    def cell_rect(self, pixel_x: int, pixel_y: int) -> pygame.Rect | None:
        """Rect (em pixels de tela) da célula sob o pixel; None se fora do grid."""
        cx, cy = self._pixel_para_celula(pixel_x, pixel_y)
        if 0 <= cy < self.rows and 0 <= cx < self.cols:
            return pygame.Rect(
                MAP_RECT.x + cx * CELL_SIZE,
                MAP_RECT.y + cy * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
        return None

    def get_cell(self, pixel_x: int, pixel_y: int) -> str:
        """Retorna o estado da célula sob o pixel; FREE se fora do grid."""
        cx, cy = self._pixel_para_celula(pixel_x, pixel_y)
        if 0 <= cy < self.rows and 0 <= cx < self.cols:
            return self._celulas[cy][cx]
        return FREE

    def set_occupied(self, cell_x: int, cell_y: int) -> None:
        """Marca uma célula como OCCUPIED (torre posicionada)."""
        if 0 <= cell_y < self.rows and 0 <= cell_x < self.cols:
            self._celulas[cell_y][cell_x] = OCCUPIED

    def set_occupied_radius(self, cell_x: int, cell_y: int, radius: int = 0) -> None:
        """Ocupa a célula central e todas num quadrado de raio `radius`.

        `radius=0` ocupa só a célula (1×1); `radius=1` ocupa 3×3, etc. Usado por
        torres maiores (ex.: Speed7, `cell_radius=1`). Não altera células PATH.
        """
        for cy in range(cell_y - radius, cell_y + radius + 1):
            for cx in range(cell_x - radius, cell_x + radius + 1):
                if 0 <= cy < self.rows and 0 <= cx < self.cols:
                    if self._celulas[cy][cx] == FREE:
                        self._celulas[cy][cx] = OCCUPIED

    def set_free(self, cell_x: int, cell_y: int) -> None:
        """Libera uma célula OCCUPIED (torre vendida); não altera PATH."""
        if 0 <= cell_y < self.rows and 0 <= cell_x < self.cols:
            if self._celulas[cell_y][cell_x] == OCCUPIED:
                self._celulas[cell_y][cell_x] = FREE

    def set_free_radius(self, cell_x: int, cell_y: int, radius: int = 0) -> None:
        """Libera a área OCCUPIED de raio `radius` (torre maior vendida)."""
        for cy in range(cell_y - radius, cell_y + radius + 1):
            for cx in range(cell_x - radius, cell_x + radius + 1):
                self.set_free(cx, cy)

    def is_placeable(self, pixel_x: int, pixel_y: int) -> bool:
        """True apenas se a célula sob o pixel está livre e dentro de MAP_RECT."""
        if not MAP_RECT.collidepoint(pixel_x, pixel_y):
            return False
        return self.get_cell(pixel_x, pixel_y) == FREE

    def is_area_placeable(self, pixel_x: int, pixel_y: int, radius: int = 0) -> bool:
        """True se toda a área de raio `radius` (em células) está livre/no mapa."""
        if not MAP_RECT.collidepoint(pixel_x, pixel_y):
            return False
        cx0, cy0 = self._pixel_para_celula(pixel_x, pixel_y)
        for cy in range(cy0 - radius, cy0 + radius + 1):
            for cx in range(cx0 - radius, cx0 + radius + 1):
                if not (0 <= cy < self.rows and 0 <= cx < self.cols):
                    return False
                if self._celulas[cy][cx] != FREE:
                    return False
        return True

    # ------------------------------------------------------------------ #
    # Render do path (modo normal de jogo)
    # ------------------------------------------------------------------ #
    def _get_path_overlay(self) -> pygame.Surface:
        """Retorna (criando se necessário) a surface cacheada do overlay de path."""
        if not hasattr(self, "_path_overlay_surf"):
            self._path_overlay_surf = pygame.Surface(MAP_RECT.size, pygame.SRCALPHA)
        return self._path_overlay_surf

    def _get_debug_overlay(self) -> pygame.Surface:
        """Retorna (criando se necessário) a surface cacheada do overlay de debug."""
        if not hasattr(self, "_debug_overlay_surf"):
            self._debug_overlay_surf = pygame.Surface(MAP_RECT.size, pygame.SRCALPHA)
        return self._debug_overlay_surf

    def draw_path(
        self,
        surface: pygame.Surface,
        time_elapsed: float | None = None,
        color: tuple[int, int, int] | None = None,
        alpha: int | None = None,
    ) -> None:
        """Desenha o caminho dos inimigos com pulsação e setas de direção.

        A faixa do caminho pulsa de alpha (respiração) e setas brancas
        percorrem cada segmento indicando o sentido do movimento. Render
        puramente decorativo (camada de UI), sem afetar a lógica.

        `color`/`alpha` permitem sobrescrever a cor (ex.: vermelho forte ao
        selecionar uma carta); sem eles, usa COR_PATH com alpha pulsante.
        `time_elapsed` (segundos) anima setas/pulsação; se None, usa o relógio.
        """
        if len(self._waypoints_px) < 2:
            return

        ticks = pygame.time.get_ticks() / 1000.0 if time_elapsed is None else time_elapsed
        cor_base = COR_PATH if color is None else color
        # Pulsação: alpha oscila suavemente entre ~50 e ~120 (se não fixado).
        pulso = alpha if alpha is not None else int(85 + 35 * math.sin(ticks * 2.0))
        overlay = self._get_path_overlay()
        overlay.fill((0, 0, 0, 0))

        # Faixa larga ligando os waypoints (coords relativas ao overlay do mapa).
        pontos = [(x - MAP_RECT.x, y - MAP_RECT.y) for x, y in self._waypoints_px]
        if len(pontos) >= 2:
            pygame.draw.lines(overlay, (*cor_base, pulso), False, pontos, CELL_SIZE // 2)
            for px, py in pontos:
                pygame.draw.circle(overlay, (*cor_base, pulso), (px, py), CELL_SIZE // 4)

        # Setas que deslizam ao longo de cada segmento (sentido do movimento).
        fase = (ticks * 0.4) % 1.0  # avança a posição das setas no tempo
        for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
            dx, dy = x1 - x0, y1 - y0
            comprimento = math.hypot(dx, dy)
            if comprimento < 1:
                continue
            ux, uy = dx / comprimento, dy / comprimento
            n = max(1, int(comprimento // CELL_SIZE))
            for i in range(n):
                t = (i + fase) / n
                ax, ay = x0 + dx * t, y0 + dy * t
                self._desenhar_seta(overlay, ax, ay, ux, uy)

        surface.blit(overlay, MAP_RECT.topleft)

    @staticmethod
    def _desenhar_seta(overlay, ax: float, ay: float, ux: float, uy: float) -> None:
        """Triângulo branco apontando na direção (ux, uy)."""
        tam = 9
        px, py = -uy, ux
        ponta = (ax + ux * tam, ay + uy * tam)
        b1 = (ax - ux * tam + px * tam * 0.7, ay - uy * tam + py * tam * 0.7)
        b2 = (ax - ux * tam - px * tam * 0.7, ay - uy * tam - py * tam * 0.7)
        pygame.draw.polygon(overlay, COR_SETA_PATH, [ponta, b1, b2])

    # ------------------------------------------------------------------ #
    # Render de debug (modo dev)
    # ------------------------------------------------------------------ #
    def draw_debug(self, surface: pygame.Surface) -> None:
        """Desenha grade cinza e realça células PATH (vermelho) e OCCUPIED (azul)."""
        overlay = self._get_debug_overlay()
        overlay.fill((0, 0, 0, 0))

        # Realce das células por estado.
        for cy in range(self.rows):
            for cx in range(self.cols):
                estado = self._celulas[cy][cx]
                if estado == PATH:
                    cor = (*COR_PATH, 120)
                elif estado == OCCUPIED:
                    cor = COR_DEBUG_OCUPADO
                else:
                    continue
                rect = pygame.Rect(
                    cx * CELL_SIZE, cy * CELL_SIZE, CELL_SIZE, CELL_SIZE
                )
                overlay.fill(cor, rect)

        # Linhas da grade (cinza semi-transparente).
        cor_linha = (*COR_GRID, 90)
        for cx in range(self.cols + 1):
            x = cx * CELL_SIZE
            pygame.draw.line(overlay, cor_linha, (x, 0), (x, MAP_RECT.height))
        for cy in range(self.rows + 1):
            y = cy * CELL_SIZE
            pygame.draw.line(overlay, cor_linha, (0, y), (MAP_RECT.width, y))

        surface.blit(overlay, MAP_RECT.topleft)
