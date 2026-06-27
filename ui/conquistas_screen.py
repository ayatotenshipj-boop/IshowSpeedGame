"""Tela de Conquistas (Bloco 6, v1.2.1).

Sub-painel do menu principal (mesma interface das telas "Em breve": método
`handle_event` retornando 'close', `draw` e `destroy`). Mostra as três
conquistas de vitória com seu estado real (desbloqueada/bloqueada). Conquistas
bloqueadas não revelam nome nem descrição ("???").
"""

import pygame
import pygame_gui

from config.settings import (
    COLOR_GOLD, COR_TEXTO, WINDOW_HEIGHT, WINDOW_WIDTH,
    COR_FUNDO_MODAL, COR_OVERLAY_MODAL, COR_FUNDO_TELA,
    COR_BRONZE, COR_MEDALHA_LENDA, COR_BLOQUEADA,
)
from core import conquistas

CENTRO_X: int = WINDOW_WIDTH // 2

# Cor da medalha por conquista quando desbloqueada.
_COR_MEDALHA: dict[str, tuple[int, int, int]] = {
    "vitoria_facil": COR_BRONZE,
    "vitoria_normal": COLOR_GOLD,
    "vitoria_dificil": COR_MEDALHA_LENDA,
}


class ConquistasScreen:
    """Painel central com as conquistas e seu estado de desbloqueio."""

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        from config.settings import FONTE_TITULO_PATH
        self._fonte_titulo = pygame.font.Font(str(FONTE_TITULO_PATH), 48)
        self._fonte_nome = pygame.font.SysFont("liberationsans", 28, bold=True)
        self._fonte_desc = pygame.font.SysFont("monospace", 20)

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
        """Escurece a tela e desenha o painel com as 3 conquistas."""
        surface.blit(self._overlay, (0, 0))
        pygame.draw.rect(surface, COR_FUNDO_MODAL, self._painel)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 1)
        # Borda-topo 3px dourada (modal-painel do HTML)
        pygame.draw.line(surface, COLOR_GOLD,
                         self._painel.topleft, self._painel.topright, 3)

        titulo = self._fonte_titulo.render("CONQUISTAS", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, self._painel.y + 46)))

        # Uma linha por conquista.
        y = self._painel.y + 110
        linha_h = 100
        for c in self._conquistas:
            self._desenhar_linha(surface, c, y)
            y += linha_h

    def _desenhar_linha(self, surface: pygame.Surface, c: dict, y: int) -> None:
        """Desenha uma conquista: medalha + nome/descrição (ou '???' se bloqueada)."""
        x = self._painel.x + 40
        desbloqueada = c["desbloqueada"]
        cor_medalha = _COR_MEDALHA.get(c["id"], COLOR_GOLD) if desbloqueada else COR_BLOQUEADA

        # Medalha: disco colorido (ouro/bronze/roxo) se desbloqueada, cinza senão.
        centro_medalha = (x + 22, y + 22)
        pygame.draw.circle(surface, cor_medalha, centro_medalha, 22)
        pygame.draw.circle(surface, COR_FUNDO_TELA, centro_medalha, 22, 2)

        tx = x + 64
        if desbloqueada:
            nome = self._fonte_nome.render(c["nome"], True, COLOR_GOLD)
            surface.blit(nome, (tx, y + 4))
            desc = self._fonte_desc.render(c["descricao"], True, COR_TEXTO)
            surface.blit(desc, (tx, y + 38))
        else:
            # Bloqueada: não revela nome nem descrição.
            nome = self._fonte_nome.render("???", True, COR_BLOQUEADA)
            surface.blit(nome, (tx, y + 14))

    def destroy(self) -> None:
        """Remove o botão Fechar do UIManager."""
        self.botao_fechar.kill()
