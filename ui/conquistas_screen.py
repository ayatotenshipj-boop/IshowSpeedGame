"""Tela de Conquistas (Bloco 6, v1.2.1).

Sub-painel do menu principal (mesma interface das telas "Em breve": método
`handle_event` retornando 'close', `draw` e `destroy`). Mostra as três
conquistas de vitória com seu estado real (desbloqueada/bloqueada). Conquistas
bloqueadas não revelam nome nem descrição ("???").
"""

import pygame
from core.asset_manager import AssetManager
import pygame_gui

from config.settings import (
    COLOR_GOLD, COR_TEXTO, WINDOW_HEIGHT, WINDOW_WIDTH,
    COR_FUNDO_MODAL, COR_OVERLAY_MODAL, COR_FUNDO_TELA,
    COR_BRONZE, COR_MEDALHA_LENDA, COR_BLOQUEADA,
    COR_BORDA_MODAL, COR_BORDA_MODAL_TOPO, COR_HUD_BORDA,
    COR_DOURADO, COR_DOURADO_ESCURO, COR_LABEL_HUD,
)
from core import conquistas

CENTRO_X: int = WINDOW_WIDTH // 2

# Cor da medalha por conquista quando desbloqueada.
_COR_MEDALHA: dict[str, tuple[int, int, int]] = {
    "vitoria_facil": COR_BRONZE,
    "vitoria_normal": COLOR_GOLD,
    "vitoria_dificil": COR_MEDALHA_LENDA,
    "vitoria_hard_2x": (255, 220, 0),  # dourado brilhante para ⚡ Sem Piedade
}


class ConquistasScreen:
    """Painel central com as conquistas e seu estado de desbloqueio."""

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._fonte_header = AssetManager.get_font("font_title", 22)  # modal header
        self._fonte_nome = AssetManager.get_font("font_title", 20)   # conquista nome
        self._fonte_desc = AssetManager.get_font("font_body", 15)  # conquista desc

        self._painel = pygame.Rect(0, 0, 640, 460)
        self._painel.center = (CENTRO_X, WINDOW_HEIGHT // 2)
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(COR_OVERLAY_MODAL)

        # Lê o estado real ao abrir.
        self._conquistas = conquistas.get_todas()

        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 70, 180, 50),
            text="Fechar",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'close' quando o botão Fechar é pressionado."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_fechar:
                return "close"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela e desenha o painel modal com cards de conquistas."""
        surface.blit(self._overlay, (0, 0))
        p = self._painel
        pygame.draw.rect(surface, COR_FUNDO_MODAL, p)
        pygame.draw.rect(surface, COR_BORDA_MODAL, p, 1)
        pygame.draw.line(surface, COR_BORDA_MODAL_TOPO, p.topleft, (p.right, p.top), 3)
        header_y = p.y + 50
        pygame.draw.line(surface, COR_HUD_BORDA, (p.x, header_y), (p.right, header_y), 1)
        grad = pygame.Surface((p.width // 2, 50), pygame.SRCALPHA)
        grad.fill((255, 208, 64, 10))
        surface.blit(grad, p.topleft)
        hdr = self._fonte_header.render("CONQUISTAS", True, COR_DOURADO)
        surface.blit(hdr, (p.x + 20, p.y + 15))

        # Cards de conquistas.
        y = p.y + 60
        card_h = 74
        card_gap = 6
        for c in self._conquistas:
            self._desenhar_card(surface, c, y)
            y += card_h + card_gap

    def _desenhar_card(self, surface: pygame.Surface, c: dict, y: int) -> None:
        """Conquista-card: medalha + nome + descrição."""
        desbloqueada = c["desbloqueada"]
        cx = self._painel.x + 16
        card_w = self._painel.width - 32
        card_rect = pygame.Rect(cx, y, card_w, 74)

        bg_cor = (14, 13, 4) if desbloqueada else (10, 10, 6)
        pygame.draw.rect(surface, bg_cor, card_rect)
        borda_cor = COR_DOURADO_ESCURO if desbloqueada else COR_HUD_BORDA
        pygame.draw.rect(surface, borda_cor, card_rect, 1)

        if not desbloqueada:
            dim = pygame.Surface(card_rect.size, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 80))
            surface.blit(dim, card_rect.topleft)

        # Medalha.
        med_cx = cx + 30
        med_cy = y + card_rect.height // 2
        cor_medalha = _COR_MEDALHA.get(c["id"], COLOR_GOLD) if desbloqueada else COR_BLOQUEADA
        pygame.draw.circle(surface, cor_medalha, (med_cx, med_cy), 20)
        pygame.draw.circle(surface, (0, 0, 0), (med_cx, med_cy), 20, 2)

        # Textos.
        tx = cx + 62
        if desbloqueada:
            nome = self._fonte_nome.render(c["nome"], True, COLOR_GOLD)
            surface.blit(nome, (tx, y + 12))
            desc = self._fonte_desc.render(c["descricao"], True, COR_LABEL_HUD)
            surface.blit(desc, (tx, y + 44))
        else:
            nome = self._fonte_nome.render("???", True, COR_BLOQUEADA)
            surface.blit(nome, (tx, y + 24))

    def destroy(self) -> None:
        """Remove o botão Fechar do UIManager."""
        self.botao_fechar.kill()
