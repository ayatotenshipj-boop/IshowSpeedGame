"""Painel de inspeção de torre (status, upgrade e venda).

Camada de UI em Pygame puro: desenha um painel flutuante quando uma torre
posicionada está selecionada, mostrando seus status (dano, alcance, cadência),
o preview do próximo nível e botões de ação (Upgrade, Vender, e — conforme o
tipo — Ativar buff / Usar habilidade). Apenas render e mapeamento de clique:
a aplicação das ações (gastar moedas, subir nível, vender) fica no main/loop.

A detecção de tipo é feita por `hasattr` (sem importar as subclasses), evitando
acoplamento com `entities/`.
"""

import pygame

from config.settings import (
    COLOR_GOLD,
    COR_TEXTO,
    MAP_RECT,
)

PANEL_W: int = 280
BTN_H: int = 30
BTN_GAP: int = 6
MARGEM: int = 14

# Cores do painel.
COR_FUNDO: tuple[int, int, int, int] = (20, 20, 35, 235)
COR_BORDA: tuple[int, int, int] = (235, 235, 235)
COR_BTN: tuple[int, int, int] = (45, 45, 75)
COR_BTN_OFF: tuple[int, int, int] = (35, 35, 45)
COR_STATS: tuple[int, int, int] = (200, 200, 210)
COR_VERDE: tuple[int, int, int] = (90, 220, 110)
COR_SETA: tuple[int, int, int] = (120, 200, 120)
COR_DESABILITADO: tuple[int, int, int] = (110, 110, 120)


class TowerPanel:
    """Desenha e trata o painel de status/upgrade/venda de uma torre."""

    def __init__(self) -> None:
        self._fonte_titulo = pygame.font.SysFont(None, 26, bold=True)
        self._fonte_stats = pygame.font.SysFont("monospace", 15)
        self._fonte_btn = pygame.font.SysFont(None, 22, bold=True)

    # ------------------------------------------------------------------ #
    # Layout (compartilhado por draw e handle_click)
    # ------------------------------------------------------------------ #
    def _botoes(self, tower) -> list[tuple[str, str, bool]]:
        """Lista de botões (action, label, habilitado) conforme o tipo/estado."""
        botoes: list[tuple[str, str, bool]] = []

        # Upgrade.
        if tower.can_upgrade():
            botoes.append(("upgrade", f"Upgrade  ${tower.upgrade_cost()}", True))
        else:
            botoes.append(("upgrade", "NÍVEL MÁXIMO", False))

        # Buff (Speed6).
        if hasattr(tower, "activate_buff"):
            if getattr(tower, "buff_active", False):
                botoes.append(("buff", "Buff ativo", False))
            elif getattr(tower, "cooldown_timer", 0.0) > 0.0:
                botoes.append(("buff", f"Cooldown {tower.cooldown_timer:.0f}s", False))
            else:
                botoes.append(("buff", "Ativar buff", True))

        # Habilidade (Speed7).
        if hasattr(tower, "use_ability"):
            usada = getattr(tower, "ability_used", False)
            botoes.append(("ability", "Habilidade usada" if usada else "Usar habilidade", not usada))

        # Vender + Fechar.
        botoes.append(("sell", f"Vender  +${tower.sell_refund()}", True))
        botoes.append(("close", "Fechar", True))
        return botoes

    def _panel_rect(self, tower) -> pygame.Rect:
        """Retângulo do painel (canto superior direito do mapa)."""
        n = len(self._botoes(tower))
        altura = 112 + n * (BTN_H + BTN_GAP) + MARGEM
        x = MAP_RECT.right - PANEL_W - 16
        y = MAP_RECT.y + 44
        return pygame.Rect(x, y, PANEL_W, altura)

    def _btn_rects(self, tower) -> list[tuple[pygame.Rect, str, str, bool]]:
        """Rects dos botões com seus (action, label, habilitado)."""
        painel = self._panel_rect(tower)
        x = painel.x + MARGEM
        w = PANEL_W - 2 * MARGEM
        y = painel.y + 108
        res = []
        for action, label, on in self._botoes(tower):
            res.append((pygame.Rect(x, y, w, BTN_H), action, label, on))
            y += BTN_H + BTN_GAP
        return res

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def handle_click(self, pos: tuple[int, int], tower) -> str | None:
        """Mapeia o clique: None se fora do painel, '' se dentro sem botão,
        senão a ação ('upgrade'|'buff'|'ability'|'sell'|'close')."""
        if not self._panel_rect(tower).collidepoint(pos):
            return None
        for rect, action, _label, _on in self._btn_rects(tower):
            if rect.collidepoint(pos):
                return action
        return ""  # clique no painel, fora de botões: consome sem ação

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, tower, coins: int) -> None:
        """Desenha o painel com status, preview de upgrade e botões."""
        painel = self._panel_rect(tower)
        fundo = pygame.Surface(painel.size, pygame.SRCALPHA)
        fundo.fill(COR_FUNDO)
        surface.blit(fundo, painel.topleft)
        pygame.draw.rect(surface, COR_BORDA, painel, 2)

        # Título.
        titulo = self._fonte_titulo.render(
            f"{tower.nome}   Nv.{tower.level}/3", True, COLOR_GOLD
        )
        surface.blit(titulo, (painel.x + MARGEM, painel.y + 12))

        # Status com preview do próximo nível.
        prox = tower.next_stats()
        linhas = [
            ("Dano", tower.damage, None if prox is None else prox[0]),
            ("Alcance", tower.range_px, None if prox is None else prox[1]),
            ("Cadência", round(tower.fire_rate, 1), None if prox is None else round(prox[2], 1)),
        ]
        y = painel.y + 44
        for nome, atual, nxt in linhas:
            txt = self._fonte_stats.render(f"{nome}: {atual}", True, COR_STATS)
            surface.blit(txt, (painel.x + MARGEM, y))
            if nxt is not None and nxt != atual:
                seta = self._fonte_stats.render(f"-> {nxt}", True, COR_SETA)
                surface.blit(seta, (painel.x + MARGEM + 150, y))
            y += 20

        # Botões.
        for rect, action, label, on in self._btn_rects(tower):
            habil = on
            if action == "upgrade" and on and coins < tower.upgrade_cost():
                habil = False  # sem moedas: aparência desabilitada
            cor_btn = COR_BTN if habil else COR_BTN_OFF
            pygame.draw.rect(surface, cor_btn, rect, border_radius=4)
            pygame.draw.rect(surface, COR_BORDA, rect, 1, border_radius=4)
            cor_txt = self._cor_label(action, habil)
            txt = self._fonte_btn.render(label, True, cor_txt)
            surface.blit(txt, txt.get_rect(center=rect.center))

    @staticmethod
    def _cor_label(action: str, habilitado: bool) -> tuple[int, int, int]:
        """Cor do texto do botão conforme ação e estado."""
        if not habilitado:
            return COR_DESABILITADO
        if action == "sell":
            return COR_VERDE
        return COR_TEXTO
