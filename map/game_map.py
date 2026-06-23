"""Renderização do mapa do estádio.

Carrega a imagem do mapa via AssetManager (nunca direto), escala para a área
jogável `MAP_RECT` e a desenha. A imagem é escalada uma única vez no boot e
mantida em cache na instância.
"""

import pygame

from config.settings import (
    CROP_BOTTOM,
    CROP_LEFT,
    CROP_RIGHT,
    CROP_TOP,
    MAP_RECT,
)
from core.asset_manager import AssetManager


class GameMap:
    """Mapa de fundo do jogo, com zoom no campo verde e escalado para `MAP_RECT`.

    Recorta a região central do estádio definida pelas frações `CROP_*` (em
    `config/settings.py`), excluindo as arquibancadas, e escala o recorte para
    preencher `MAP_RECT`. Os waypoints do path são recalculados pelas mesmas
    frações em `PlacementGrid`, mantendo o caminho alinhado ao campo.
    """

    def __init__(self, assets: AssetManager) -> None:
        original = assets.get("mapa")
        recorte = self._recorte(original)
        # smoothscale dá um resultado mais limpo que scale para top-down.
        self._imagem: pygame.Surface = pygame.transform.smoothscale(
            recorte, MAP_RECT.size
        )

    @staticmethod
    def _recorte(original: pygame.Surface) -> pygame.Surface:
        """Recorta a região `CROP_*` da imagem (foco no campo, sem arquibancada)."""
        ow, oh = original.get_size()
        x0 = int(ow * CROP_LEFT)
        y0 = int(oh * CROP_TOP)
        x1 = int(ow * CROP_RIGHT)
        y1 = int(oh * CROP_BOTTOM)
        rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0).clip(original.get_rect())
        return original.subsurface(rect).copy()

    def draw(self, surface: pygame.Surface) -> None:
        """Desenha o mapa no topo-esquerdo de `MAP_RECT`."""
        surface.blit(self._imagem, MAP_RECT.topleft)
