"""Widget de seleção de dificuldade in-game.

Aparece no canto superior esquerdo do mapa por 10 segundos ao iniciar
a partida. O jogador clica para escolher; após o timeout, a dificuldade
selecionada (padrão: Normal) é confirmada e o widget desaparece.

Baseado em difficulty_selector_astd.html.
"""

import pygame

from config.settings import (
    COLOR_GOLD,
    COR_BORDA_SUTIL,
    COR_FUNDO_MODAL,
    COR_LABEL_HUD,
    COR_TEXTO,
    FONTE_TITULO_PATH,
    MAP_RECT,
)
from ui.hud import TOP_BAR_HEIGHT

# Dados de cada dificuldade: label, sublabel, cor de destaque, cor bg selecionado.
_DIFS = {
    "facil":   {"label": "FÁCIL",   "sub": "tranquilo",   "cor": (29, 158, 117), "bg": (10, 40, 28)},
    "normal":  {"label": "NORMAL",  "sub": "equilibrado", "cor": (36, 120, 200), "bg": (10, 28, 50)},
    "dificil": {"label": "DIFÍCIL", "sub": "sem piedade", "cor": (190, 60, 30),  "bg": (50, 16, 8)},
}

_CARD_W   = 84
_CARD_H   = 68
_GAP      = 8
_PAD      = 12
_TITLE_H  = 22
_DURATION = 10.0


class DiffSelectorWidget:
    """Widget sutil de seleção de dificuldade. Visível por 10s."""

    def __init__(self) -> None:
        self.visible: bool = True
        self.timer: float = _DURATION
        self.modo_selecionado: str = "normal"

        self._fonte_label = pygame.font.Font(str(FONTE_TITULO_PATH), 14)
        self._fonte_sub   = pygame.font.SysFont("monospace", 11)
        self._fonte_title = pygame.font.SysFont("monospace", 11)
        self._fonte_cd    = pygame.font.SysFont("monospace", 11)

        total_w = _PAD + len(_DIFS) * _CARD_W + (len(_DIFS) - 1) * _GAP + _PAD
        total_h = _PAD + _TITLE_H + _GAP + _CARD_H + _PAD + 6  # +6 barra progresso

        # Posição: canto superior esquerdo, abaixo da barra de HUD.
        x = MAP_RECT.x + 10
        y = MAP_RECT.y + TOP_BAR_HEIGHT + 8
        self._panel = pygame.Rect(x, y, total_w, total_h)

        # Rects dos cards na ordem.
        cards_x = x + _PAD
        cards_y = y + _PAD + _TITLE_H + _GAP
        self._card_rects: dict[str, pygame.Rect] = {}
        for i, modo in enumerate(_DIFS):
            self._card_rects[modo] = pygame.Rect(
                cards_x + i * (_CARD_W + _GAP), cards_y, _CARD_W, _CARD_H
            )

        # Botão "⚡ 2×": abaixo do card Difícil, visível apenas quando selecionado.
        dificil_card = self._card_rects["dificil"]
        self._btn_2x_rect = pygame.Rect(dificil_card.x, self._panel.bottom + 4, _CARD_W, 20)

        # Surface SRCALPHA reutilizada.
        self._overlay_surf = pygame.Surface(self._panel.size, pygame.SRCALPHA)

    # ── Input ────────────────────────────────────────────────────────────────
    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """Retorna o modo clicado ('facil'|'normal'|'dificil'|'dificil_2x') ou None."""
        if not self.visible:
            return None
        # Botão 2× aparece quando dificil já está selecionado.
        if self.modo_selecionado == "dificil" and self._btn_2x_rect.collidepoint(pos):
            self.visible = False
            return "dificil_2x"
        for modo, rect in self._card_rects.items():
            if rect.collidepoint(pos):
                self.modo_selecionado = modo
                self.visible = False
                return modo
        return None

    def update(self, dt: float) -> str | None:
        """Ticks o countdown. Retorna o modo ao expirar ou None."""
        if not self.visible:
            return None
        self.timer -= dt
        if self.timer <= 0.0:
            self.visible = False
            return self.modo_selecionado
        return None

    # ── Render ────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        p = self._panel
        mx, my = pygame.mouse.get_pos()

        # Fundo semi-transparente do painel.
        self._overlay_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(self._overlay_surf, (*COR_FUNDO_MODAL, 220),
                         (0, 0, p.width, p.height))
        pygame.draw.rect(self._overlay_surf, (*COR_BORDA_SUTIL, 200),
                         (0, 0, p.width, p.height), 1)
        # Borda dourada 2px no topo.
        pygame.draw.line(self._overlay_surf, (*COLOR_GOLD, 200),
                         (0, 0), (p.width, 0), 2)
        surface.blit(self._overlay_surf, p.topleft)

        # Título "DIFICULDADE".
        title = self._fonte_title.render("DIFICULDADE", True, COR_LABEL_HUD)
        surface.blit(title, (p.x + _PAD, p.y + _PAD + 4))

        # Countdown à direita do título.
        cd_txt = self._fonte_cd.render(f"{max(0, int(self.timer) + 1)}s", True, COR_LABEL_HUD)
        surface.blit(cd_txt, (p.right - _PAD - cd_txt.get_width(), p.y + _PAD + 4))

        # Cards.
        for modo, rect in self._card_rects.items():
            info = _DIFS[modo]
            selecionado = modo == self.modo_selecionado
            hover = rect.collidepoint(mx, my)

            # Fundo do card.
            cor_bg = info["bg"] if selecionado else (8, 8, 6)
            if hover and not selecionado:
                cor_bg = (18, 18, 10)
            pygame.draw.rect(surface, cor_bg, rect)

            # Borda: cor de destaque se selecionado, dim se não.
            cor_borda = info["cor"] if selecionado else (37, 34, 0)
            borda_w = 2 if selecionado else 1
            pygame.draw.rect(surface, cor_borda, rect, borda_w)

            # Dot de seleção (canto superior direito do card).
            if selecionado:
                pygame.draw.circle(surface, info["cor"],
                                   (rect.right - 7, rect.top + 7), 4)

            # Label (Bebas Neue, cor de destaque se selecionado).
            cor_label = info["cor"] if selecionado else COR_TEXTO
            label = self._fonte_label.render(info["label"], True, cor_label)
            surface.blit(label, label.get_rect(center=(rect.centerx, rect.centery - 8)))

            # Sublabel.
            sub = self._fonte_sub.render(info["sub"], True, COR_LABEL_HUD)
            surface.blit(sub, sub.get_rect(center=(rect.centerx, rect.centery + 14)))

        # Botão "⚡ 2×" abaixo do card Difícil (visível quando dificil selecionado).
        if self.modo_selecionado == "dificil":
            btn = self._btn_2x_rect
            hover_btn = btn.collidepoint(mx, my)
            cor_btn = (70, 20, 8) if hover_btn else (50, 16, 8)
            pygame.draw.rect(surface, cor_btn, btn)
            pygame.draw.rect(surface, (190, 60, 30), btn, 1)
            label_2x = self._fonte_sub.render("⚡ INICIAR EM 2×", True, (255, 200, 64))
            surface.blit(label_2x, label_2x.get_rect(center=btn.center))

        # Barra de progresso do countdown (fundo da barra).
        bar_y = p.bottom - 7
        ratio = max(0.0, self.timer / _DURATION)
        bar_w = int((p.width - 2) * ratio)
        pygame.draw.rect(surface, (26, 24, 0), (p.x + 1, bar_y, p.width - 2, 4))
        if bar_w > 0:
            pygame.draw.rect(surface, COLOR_GOLD, (p.x + 1, bar_y, bar_w, 4))
