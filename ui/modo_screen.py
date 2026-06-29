"""Tela de seleção de dificuldade (Bloco 5, v1.2.1).

Exibida após o jogador clicar JOGAR, antes da intro/partida. Três modos
(Fácil/Normal/Difícil) + Voltar. `handle_event` retorna a chave do modo
escolhido ("facil"|"normal"|"dificil"), "voltar" ou None.
"""

import pygame
from core.asset_manager import AssetManager
import pygame_gui

from config.settings import (
    COLOR_GOLD,
    COR_FUNDO_TELA,
    COR_TEXTO,
    COR_VERDE_NEON,
    COR_DOURADO,
    COR_VERMELHO,
    MODOS_DIFICULDADE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

BTN_W: int = 320
BTN_H: int = 56
CENTRO_X: int = WINDOW_WIDTH // 2

# Cores HTML: fácil → --verde-neon, normal → --dourado, difícil → --vermelho
_ORDEM: list[str] = ["facil", "normal", "dificil"]
_CORES: dict[str, tuple[int, int, int]] = {
    "facil":   COR_VERDE_NEON,
    "normal":  COR_DOURADO,
    "dificil": COR_VERMELHO,
}


class ModoScreen:
    """Seleção de dificuldade antes da partida."""

    def __init__(self, manager: pygame_gui.UIManager, assets=None) -> None:
        self._fonte_titulo = AssetManager.get_font("font_title", 56)
        self._fonte_desc = AssetManager.get_font("font_body", 22)

        # Fundo: mapa escurecido (se disponível) ou cor neutra.
        self._bg: pygame.Surface | None = None
        if assets is not None:
            try:
                bg = pygame.transform.smoothscale(
                    assets.get("mapa"), (WINDOW_WIDTH, WINDOW_HEIGHT)
                ).copy()
                escuro = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                escuro.fill((0, 0, 0, 175))
                bg.blit(escuro, (0, 0))
                self._bg = bg
            except KeyError:
                self._bg = None

        # Um botão por modo, empilhados ao centro.
        y0 = 220
        self._botoes: dict[str, pygame_gui.elements.UIButton] = {}
        self._y_btn: dict[str, int] = {}
        for i, chave in enumerate(_ORDEM):
            cy = y0 + i * 96
            self._y_btn[chave] = cy
            self._botoes[chave] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(CENTRO_X - BTN_W // 2, cy, BTN_W, BTN_H),
                text=MODOS_DIFICULDADE[chave]["nome"],
                manager=manager,
            )
        self.botao_voltar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 110, y0 + 3 * 96 + 8, 220, 48),
            text="VOLTAR",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'facil'|'normal'|'dificil'|'voltar' ao clicar, senão None."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_voltar:
                return "voltar"
            for chave, botao in self._botoes.items():
                if event.ui_element == botao:
                    return chave
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Fundo, título e a descrição de cada modo abaixo do respectivo botão."""
        if self._bg is not None:
            surface.blit(self._bg, (0, 0))
        else:
            surface.fill(COR_FUNDO_TELA)

        titulo = self._fonte_titulo.render("SELECIONE A DIFICULDADE", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, 120)))

        for chave in _ORDEM:
            desc = MODOS_DIFICULDADE[chave]["descricao"]
            cor = _CORES.get(chave, COR_TEXTO)
            txt = self._fonte_desc.render(desc, True, cor)
            # Descrição logo abaixo do botão do modo.
            cy = self._y_btn[chave] + BTN_H + 14
            surface.blit(txt, txt.get_rect(center=(CENTRO_X, cy)))

    def destroy(self) -> None:
        """Remove os botões do UIManager."""
        for botao in self._botoes.values():
            botao.kill()
        self.botao_voltar.kill()
