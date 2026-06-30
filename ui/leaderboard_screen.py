"""Tela do leaderboard global (top 10), buscado do Supabase em thread.

Painel central em Pygame puro; botão FECHAR via pygame_gui. A busca roda numa
thread no __init__ para não travar o jogo; enquanto isso exibe "Buscando...".
Abas permitem alternar entre categorias (Normal / Difícil / Infinito).
"""

import threading

import pygame
from core.asset_manager import AssetManager
import pygame_gui

from config.settings import (
    COLOR_GOLD, COR_TEXTO, COR_CIANO, WINDOW_HEIGHT, WINDOW_WIDTH,
    COR_FUNDO_MODAL, COR_OVERLAY_LB, COR_PRATA, COR_BRONZE,
)
from core.leaderboard import CATEGORIAS, buscar_top10, formatar_tempo

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2


class LeaderboardScreen:
    """Painel 700×500 com o top 10 global (busca assíncrona).

    Suporta três abas de categoria: Normal, Difícil e Infinito.
    Trocar de aba dispara nova busca em thread — sem travar o loop principal.
    """

    PAINEL_W: int = 700
    PAINEL_H: int = 500

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._fonte_titulo = AssetManager.get_font("font_title", 42)   # BebasNeue
        self._fonte_cab = AssetManager.get_font("font_body", 18)              # Share Tech Mono
        self._fonte_pos = AssetManager.get_font("font_title", 28)      # BebasNeue posições
        self._fonte_nome = AssetManager.get_font("font_hud", 20)  # Oswald→Liberation
        self._fonte_mono = AssetManager.get_font("font_body", 20)             # tempo/data
        self._fonte_msg = AssetManager.get_font("font_body", 26)
        self._fonte_aba = AssetManager.get_font("font_hud", 14)   # rótulo das abas

        self._painel = pygame.Rect(0, 0, self.PAINEL_W, self.PAINEL_H)
        self._painel.center = (CENTRO_X, CENTRO_Y)
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(COR_OVERLAY_LB)

        # Categoria ativa (padrão: normal_speedrun).
        self._categoria_ativa: str = "normal_speedrun"

        # Abas clicáveis: 3 Rects dispostos horizontalmente abaixo do título.
        tab_w, tab_h, tab_gap = 180, 24, 10
        total_tab_w = len(CATEGORIAS) * tab_w + (len(CATEGORIAS) - 1) * tab_gap
        tab_x0 = self._painel.x + (self.PAINEL_W - total_tab_w) // 2
        tab_y = self._painel.y + 57
        self._tabs: list[tuple[str, pygame.Rect]] = [
            (chave, pygame.Rect(tab_x0 + i * (tab_w + tab_gap), tab_y, tab_w, tab_h))
            for i, chave in enumerate(CATEGORIAS)
        ]

        # Estado da busca (preenchido pela thread).
        self.carregando: bool = True
        self.entradas: list[dict] = []
        # Geração da busca: incrementada a cada troca de aba para invalidar
        # resultados de threads anteriores que cheguem atrasados.
        self._gen: int = 0
        threading.Thread(target=self._buscar, args=(self._gen,), daemon=True).start()

        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 70, 180, 48),
            text="FECHAR",
            manager=manager,
        )

    def _buscar(self, gen: int) -> None:
        """Busca top 10 da categoria ativa; descarta resultado se a aba mudou."""
        entradas = buscar_top10(self._categoria_ativa)
        if gen == self._gen:  # ignora thread obsoleta de aba anterior
            self.entradas = entradas
            self.carregando = False

    def _rebuscar(self) -> None:
        """Reinicia a busca ao trocar de categoria; exibe 'Buscando...' enquanto aguarda."""
        self.carregando = True
        self.entradas = []
        self._gen += 1
        threading.Thread(target=self._buscar, args=(self._gen,), daemon=True).start()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True quando FECHAR é pressionado; trata cliques nas abas de categoria."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.botao_fechar:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for chave, rect in self._tabs:
                if rect.collidepoint(event.pos):
                    if chave != self._categoria_ativa:
                        self._categoria_ativa = chave
                        self._rebuscar()
                    return False
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela, desenha o painel, abas, cabeçalho e a tabela/estado."""
        surface.blit(self._overlay, (0, 0))
        pygame.draw.rect(surface, COR_FUNDO_MODAL, self._painel)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 1)
        # Borda-topo 3px dourada (como no HTML: border-top: 3px solid --dourado)
        pygame.draw.line(surface, COLOR_GOLD,
                         self._painel.topleft, self._painel.topright, 3)

        titulo = self._fonte_titulo.render("LEADERBOARD GLOBAL", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, self._painel.y + 36)))

        # Abas de categoria (Normal / Difícil / Infinito).
        for chave, rect in self._tabs:
            ativo = chave == self._categoria_ativa
            cor_fundo = (60, 50, 0) if ativo else (30, 28, 14)
            cor_borda = COLOR_GOLD if ativo else (60, 55, 30)
            pygame.draw.rect(surface, cor_fundo, rect)
            pygame.draw.rect(surface, cor_borda, rect, 1)
            label = CATEGORIAS[chave]["label"]
            cor_label = COLOR_GOLD if ativo else COR_TEXTO
            txt = self._fonte_aba.render(label, True, cor_label)
            surface.blit(txt, txt.get_rect(center=rect.center))

        if self.carregando:
            # Texto piscante "Buscando recordes...".
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                msg = self._fonte_msg.render("Buscando recordes...", True, COR_TEXTO)
                surface.blit(msg, msg.get_rect(center=(CENTRO_X, CENTRO_Y)))
            return

        if not self.entradas:
            # Mensagem contextual para categoria sem registros.
            if self._categoria_ativa == "infinite_waves":
                txt_vazio = "Seja o primeiro a jogar o Modo Infinito!"
            else:
                txt_vazio = "Nenhum recorde ainda. Seja o primeiro!"
            msg = self._fonte_msg.render(txt_vazio, True, COR_TEXTO)
            surface.blit(msg, msg.get_rect(center=(CENTRO_X, CENTRO_Y)))
            return

        # Cabeçalho da tabela — coluna de score varia por categoria.
        _infinito = self._categoria_ativa == "infinite_waves"
        cab_score = "WAVES" if _infinito else "TEMPO"
        x = self._painel.x
        col_pos = x + 40
        col_nome = x + 110
        col_tempo = x + 400
        col_data = x + 540
        y = self._painel.y + 100
        for texto, cx in (("#", col_pos), ("NOME", col_nome), (cab_score, col_tempo), ("DATA", col_data)):
            cab = self._fonte_cab.render(texto, True, COLOR_GOLD)
            surface.blit(cab, (cx, y))
        y += 38

        # Linhas do top 10: posição em BebasNeue grande, nome em negrito, score em mono.
        for i, e in enumerate(self.entradas):
            cor = self._cor_posicao(i)
            pos = self._fonte_pos.render(f"{i + 1}", True, cor)
            nome = self._fonte_nome.render(str(e.get("nome", "?"))[:16], True, cor)
            if _infinito:
                # Infinito: exibe número de waves (inteiro), não tempo formatado.
                score_str = str(int(e.get("valor") or 0))
            else:
                score_str = formatar_tempo(float(e.get("tempo") or 0))
            score = self._fonte_mono.render(score_str, True, COR_CIANO)
            cor_data = (68, 68, 68)
            data = self._fonte_cab.render(str(e.get("data", "")), True, cor_data)
            surface.blit(pos, (col_pos, y))
            surface.blit(nome, (col_nome, y))
            surface.blit(score, (col_tempo, y))
            surface.blit(data, (col_data, y + 4))
            y += 32

    @staticmethod
    def _cor_posicao(indice: int) -> tuple[int, int, int]:
        """Cor da linha conforme a posição (ouro/prata/bronze/branco)."""
        return {0: COLOR_GOLD, 1: COR_PRATA, 2: COR_BRONZE}.get(indice, COR_TEXTO)

    def destroy(self) -> None:
        """Remove o botão FECHAR do UIManager."""
        self.botao_fechar.kill()
