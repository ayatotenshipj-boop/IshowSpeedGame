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


_CARD_H: int = 74
_CARD_GAP: int = 6
_CARD_STRIDE: int = _CARD_H + _CARD_GAP
_HEADER_H: int = 60   # altura reservada ao cabeçalho
_FOOTER_H: int = 70   # altura reservada ao botão Fechar


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

        # Scroll — necessário quando conquistas excedem área visível.
        self._scroll: int = 0
        conteudo_h = len(self._conquistas) * _CARD_STRIDE
        area_h = self._painel.height - _HEADER_H - _FOOTER_H
        self._max_scroll: int = max(0, conteudo_h - area_h)

        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 70, 180, 50),
            text="Fechar",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'close' quando o botão Fechar é pressionado. Trata scroll da lista."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_fechar:
                return "close"
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(self._scroll - event.y * 20, self._max_scroll))
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

        # Área scrollável — clip impede cards de vazar sobre header e footer.
        area_top = p.y + _HEADER_H
        area_bottom = p.bottom - _FOOTER_H
        area_rect = pygame.Rect(p.x, area_top, p.width, area_bottom - area_top)
        prev_clip = surface.get_clip()
        surface.set_clip(area_rect)

        y = area_top - self._scroll
        for c in self._conquistas:
            self._desenhar_card(surface, c, y)
            y += _CARD_STRIDE

        surface.set_clip(prev_clip)

        # Indicador de scroll (barra lateral discreta) quando há conteúdo fora.
        if self._max_scroll > 0:
            bar_x = p.right - 8
            bar_h = area_rect.height
            thumb_h = max(20, bar_h * bar_h // (bar_h + self._max_scroll))
            thumb_y = area_top + int((bar_h - thumb_h) * self._scroll / self._max_scroll)
            pygame.draw.rect(surface, (40, 38, 20), pygame.Rect(bar_x, area_top, 6, bar_h))
            pygame.draw.rect(surface, COR_DOURADO_ESCURO, pygame.Rect(bar_x, thumb_y, 6, thumb_h), border_radius=3)

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
