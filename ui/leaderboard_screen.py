"""Tela do leaderboard global (top 10), buscado do Supabase em thread.

Painel central em Pygame puro; botão FECHAR via pygame_gui. A busca roda numa
thread no __init__ para não travar o jogo; enquanto isso exibe "Buscando...".
"""

import threading

import pygame
import pygame_gui

from config.settings import COLOR_GOLD, COLOR_HUD_BG, COR_TEXTO, WINDOW_HEIGHT, WINDOW_WIDTH
from core.leaderboard import buscar_top10, formatar_tempo

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2

# Cores por posição.
COR_OURO: tuple[int, int, int] = (255, 200, 50)
COR_PRATA: tuple[int, int, int] = (192, 192, 192)
COR_BRONZE: tuple[int, int, int] = (205, 127, 50)


class LeaderboardScreen:
    """Painel 700×500 com o top 10 global (busca assíncrona)."""

    PAINEL_W: int = 700
    PAINEL_H: int = 500

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._fonte_titulo = pygame.font.SysFont(None, 52, bold=True)
        self._fonte_cab = pygame.font.SysFont(None, 30, bold=True)
        self._fonte = pygame.font.SysFont(None, 30)
        self._fonte_msg = pygame.font.SysFont(None, 36)

        self._painel = pygame.Rect(0, 0, self.PAINEL_W, self.PAINEL_H)
        self._painel.center = (CENTRO_X, CENTRO_Y)

        # Estado da busca (preenchido pela thread).
        self.carregando: bool = True
        self.entradas: list[dict] = []
        threading.Thread(target=self._buscar, daemon=True).start()

        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 70, 180, 48),
            text="FECHAR",
            manager=manager,
        )

    def _buscar(self) -> None:
        """Busca o top 10 (thread); ao terminar marca carregando=False."""
        self.entradas = buscar_top10()
        self.carregando = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True quando FECHAR é pressionado."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.botao_fechar:
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela, desenha o painel, cabeçalho e a tabela/estado."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, COLOR_HUD_BG, self._painel, border_radius=14)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 3, border_radius=14)

        titulo = self._fonte_titulo.render("🏆 LEADERBOARD GLOBAL", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, self._painel.y + 44)))

        if self.carregando:
            # Texto piscante "Buscando recordes...".
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                msg = self._fonte_msg.render("Buscando recordes...", True, COR_TEXTO)
                surface.blit(msg, msg.get_rect(center=(CENTRO_X, CENTRO_Y)))
            return

        if not self.entradas:
            msg = self._fonte_msg.render(
                "Nenhum recorde ainda. Seja o primeiro!", True, COR_TEXTO
            )
            surface.blit(msg, msg.get_rect(center=(CENTRO_X, CENTRO_Y)))
            return

        # Cabeçalho da tabela (colunas: #  NOME  TEMPO  DATA).
        x = self._painel.x
        col_pos = x + 40
        col_nome = x + 110
        col_tempo = x + 400
        col_data = x + 540
        y = self._painel.y + 100
        for texto, cx in (("#", col_pos), ("NOME", col_nome), ("TEMPO", col_tempo), ("DATA", col_data)):
            cab = self._fonte_cab.render(texto, True, COLOR_GOLD)
            surface.blit(cab, (cx, y))
        y += 38

        # Linhas do top 10.
        for i, e in enumerate(self.entradas):
            cor = self._cor_posicao(i)
            pos = self._fonte.render(f"{i + 1}", True, cor)
            nome = self._fonte.render(str(e.get("nome", "?"))[:16], True, cor)
            tempo = self._fonte.render(formatar_tempo(float(e.get("tempo", 0))), True, cor)
            data = self._fonte.render(str(e.get("data", "")), True, cor)
            surface.blit(pos, (col_pos, y))
            surface.blit(nome, (col_nome, y))
            surface.blit(tempo, (col_tempo, y))
            surface.blit(data, (col_data, y))
            y += 32

    @staticmethod
    def _cor_posicao(indice: int) -> tuple[int, int, int]:
        """Cor da linha conforme a posição (ouro/prata/bronze/branco)."""
        return {0: COR_OURO, 1: COR_PRATA, 2: COR_BRONZE}.get(indice, COR_TEXTO)

    def destroy(self) -> None:
        """Remove o botão FECHAR do UIManager."""
        self.botao_fechar.kill()
