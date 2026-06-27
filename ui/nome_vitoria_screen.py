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
COR_AVISO: tuple[int, int, int] = (220, 140, 40)
COR_RECORDE: tuple[int, int, int] = (60, 200, 100)


class NomeVitoriaScreen:
    """Pede o nome do jogador vitorioso; alimenta o leaderboard."""

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        tempo: float,
        record_anterior: dict | None = None,
    ) -> None:
        self._manager = manager
        self._tempo = tempo
        self._record_anterior = record_anterior  # {'nome': ..., 'tempo': ...} | None

        self._fonte_titulo = pygame.font.SysFont(None, 96, bold=True)
        self._fonte_tempo  = pygame.font.SysFont(None, 52)
        self._fonte_label  = pygame.font.SysFont(None, 36)
        self._fonte_aviso  = pygame.font.SysFont(None, 30)

        # Novo record?
        self._novo_record = (
            record_anterior is None
            or tempo < record_anterior.get("tempo", float("inf"))
        )

        self.campo_nome = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(CENTRO_X - 200, CENTRO_Y + 10, 400, 50),
            manager=manager,
        )
        self.campo_nome.set_text_length_limit(16)
        # Preenche com o nome anterior para facilitar re-uso.
        if record_anterior and record_anterior.get("nome"):
            self.campo_nome.set_text(record_anterior["nome"])
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
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.campo_nome:
            return self.campo_nome.get_text().strip()
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_HUD_BG)

        titulo = self._fonte_titulo.render("VOCÊ ZEROU!", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, CENTRO_Y - 170)))

        tempo_txt = self._fonte_tempo.render(
            f"Tempo: {formatar_tempo(self._tempo)}", True, COR_CIANO
        )
        surface.blit(tempo_txt, tempo_txt.get_rect(center=(CENTRO_X, CENTRO_Y - 100)))

        # Record anterior (se existe).
        if self._record_anterior:
            rec = self._record_anterior
            rec_txt = self._fonte_aviso.render(
                f"Seu record: {rec.get('nome', '?')}  {formatar_tempo(rec.get('tempo', 0))}",
                True,
                COR_RECORDE,
            )
            surface.blit(rec_txt, rec_txt.get_rect(center=(CENTRO_X, CENTRO_Y - 58)))

        # Aviso se não bateu o record.
        if not self._novo_record:
            aviso = self._fonte_aviso.render(
                "Tempo não bateu seu record — nome não será atualizado no leaderboard.",
                True,
                COR_AVISO,
            )
            surface.blit(aviso, aviso.get_rect(center=(CENTRO_X, CENTRO_Y - 30)))

        label_txt = "Digite seu nome para o leaderboard:" if self._novo_record else "Digite mesmo assim para registrar próxima vez:"
        label = self._fonte_label.render(label_txt, True, COR_TEXTO)
        surface.blit(label, label.get_rect(center=(CENTRO_X, CENTRO_Y - 30 if self._novo_record else CENTRO_Y - 5)))

    def destroy(self) -> None:
        self.campo_nome.kill()
        self.botao_confirmar.kill()
        self.botao_pular.kill()
