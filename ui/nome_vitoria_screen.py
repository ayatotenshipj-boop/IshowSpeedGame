"""Tela que pede o nome do jogador após zerar (para o leaderboard global).

pygame_gui para o campo de texto e botões; fundo/títulos em Pygame puro.
`handle_event` retorna o nome (CONFIRMAR), "" (PULAR) ou None (aguardando).
"""

import pygame
import pygame_gui

from config.settings import COLOR_GOLD, COLOR_HUD_BG, COR_TEXTO, WINDOW_HEIGHT, WINDOW_WIDTH
from core.leaderboard import formatar_tempo

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2
COR_CIANO: tuple[int, int, int] = (80, 220, 230)


class NomeVitoriaScreen:
    """Pede o nome do jogador vitorioso; alimenta o leaderboard."""

    def __init__(self, manager: pygame_gui.UIManager, tempo: float) -> None:
        self._manager = manager
        self._tempo = tempo
        self._fonte_titulo = pygame.font.SysFont(None, 96, bold=True)
        self._fonte_tempo = pygame.font.SysFont(None, 52)
        self._fonte_label = pygame.font.SysFont(None, 36)

        self.campo_nome = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(CENTRO_X - 200, CENTRO_Y + 10, 400, 50),
            manager=manager,
        )
        self.campo_nome.set_text_length_limit(16)
        self.campo_nome.focus()

        self.botao_confirmar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 210, CENTRO_Y + 90, 200, 56),
            text="CONFIRMAR",
            manager=manager,
        )
        self.botao_pular = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X + 10, CENTRO_Y + 90, 200, 56),
            text="PULAR",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna o nome (CONFIRMAR / Enter), "" (PULAR) ou None (aguardando)."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_confirmar:
                return self.campo_nome.get_text().strip()
            if event.ui_element == self.botao_pular:
                return ""
        # Enter no campo de texto confirma.
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.campo_nome:
            return self.campo_nome.get_text().strip()
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Título, tempo e instrução (o campo/botões são do UIManager)."""
        surface.fill(COLOR_HUD_BG)

        titulo = self._fonte_titulo.render("VOCÊ ZEROU!", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, CENTRO_Y - 160)))

        tempo = self._fonte_tempo.render(
            f"Tempo: {formatar_tempo(self._tempo)}", True, COR_CIANO
        )
        surface.blit(tempo, tempo.get_rect(center=(CENTRO_X, CENTRO_Y - 90)))

        label = self._fonte_label.render(
            "Digite seu nome para o leaderboard:", True, COR_TEXTO
        )
        surface.blit(label, label.get_rect(center=(CENTRO_X, CENTRO_Y - 30)))

    def destroy(self) -> None:
        """Remove os elementos do UIManager."""
        self.campo_nome.kill()
        self.botao_confirmar.kill()
        self.botao_pular.kill()
