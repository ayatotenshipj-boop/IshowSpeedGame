"""HUD do jogo — barra superior (32px) com stats e botões de controle.

Layout:
  [$ coins] [Mortes kills] [Onda n/N] [MM:SS] [Vidas n]   …   [SKIP] [AUTO] [2×]
  ─────────────────── borda inferior 1px #1a1800 ───────────────────────────────
  (mapa)  Boss alert / countdown aparece abaixo desta barra, sobre o mapa.

Estilo btn-hud (HTML de referência):
  inativo : bg #111108, borda dim, texto dim
  hover   : borda dourada, texto dourado, bg #1a1800
  ativo   : fundo dourado, texto escuro, borda dourada
  skip    : borda verde-neon, texto verde-neon
"""

import pygame
from core.asset_manager import AssetManager

from config.settings import (
    COLOR_CARD_BG,
    COLOR_GOLD,
    COR_BOSS_ALERTA,
    COR_BORDA_SUTIL,
    COR_BTN_HUD_ATIVO_TX,
    COR_BTN_HUD_HOVER_BG,
    COR_BTN_HUD_TEXTO,
    COR_CIANO,
    COR_HUD_BARRA_BG,
    COR_HUD_BORDA,
    COR_INF_BADGE,
    COR_LABEL_HUD,
    COR_TEXTO,
    COR_VERDE_NEON,
    COR_VIDA_ALERTA,
    COR_VIDA_CRITICA,
    COR_VIDA_OK,
    MAP_RECT,
)

TOP_BAR_HEIGHT: int = 32

# ── Geometria dos botões (inline na barra) ──────────────────────────────────
_BTN_H   = 22
_BTN_Y   = MAP_RECT.y + (TOP_BAR_HEIGHT - _BTN_H) // 2   # 5px — centrado
_SPEED_W = 44
_AUTO_W  = 50
_SKIP_W  = 130
_GAP     = 8
_PAD_R   = 12

SPEED_BTN_RECT: pygame.Rect = pygame.Rect(
    MAP_RECT.right - _PAD_R - _SPEED_W, _BTN_Y, _SPEED_W, _BTN_H
)
AUTO_BTN_RECT: pygame.Rect = pygame.Rect(
    SPEED_BTN_RECT.left - _GAP - _AUTO_W, _BTN_Y, _AUTO_W, _BTN_H
)
SKIP_BTN_RECT: pygame.Rect = pygame.Rect(
    AUTO_BTN_RECT.left - _GAP - _SKIP_W, _BTN_Y, _SKIP_W, _BTN_H
)


class HUD:
    """Barra superior de informações e controles da partida."""

    def __init__(self) -> None:
        self._fonte_stat  = AssetManager.get_font("font_hud", 15)
        self._fonte_label = AssetManager.get_font("font_body", 13)
        self._fonte_btn   = AssetManager.get_font("font_hud", 13)
        self._fonte_alert = AssetManager.get_font("font_hud", 16)
        self._fonte_cd    = AssetManager.get_font("font_body", 14)

    # ── API pública (rects para detecção de clique no main) ─────────────────
    @staticmethod
    def speed_button_rect() -> pygame.Rect:
        return SPEED_BTN_RECT

    @staticmethod
    def skip_button_rect() -> pygame.Rect:
        return SKIP_BTN_RECT

    @staticmethod
    def auto_button_rect() -> pygame.Rect:
        return AUTO_BTN_RECT

    # ── Render principal ─────────────────────────────────────────────────────
    def draw(
        self,
        surface: pygame.Surface,
        coins: int,
        lives: int,
        wave: int,
        next_wave_in: float | None = None,
        total_waves: int = 15,
        boss_wave: bool = False,
        kills: int = 0,
        speed_multiplier: float = 1.0,
        tempo_decorrido: float | None = None,
        skip_disponivel: bool = False,
        skip_bonus: int = 0,
        auto_skip: bool = False,
        modo_infinito: bool = False,
        prox_boss_wave: int | None = None,
    ) -> None:
        bx = MAP_RECT.x
        by = MAP_RECT.y
        bw = MAP_RECT.width

        # Fundo da barra + borda inferior.
        pygame.draw.rect(surface, COR_HUD_BARRA_BG, (bx, by, bw, TOP_BAR_HEIGHT))
        pygame.draw.line(
            surface, COR_HUD_BORDA,
            (bx, by + TOP_BAR_HEIGHT - 1), (bx + bw, by + TOP_BAR_HEIGHT - 1),
        )

        meio_y = by + TOP_BAR_HEIGHT // 2

        # ── Badge [INFINITO] (à esquerda, antes dos stats) ───────────────────
        if modo_infinito:
            badge = self._fonte_btn.render("[INFINITO]", True, COR_INF_BADGE)
            surface.blit(badge, badge.get_rect(midleft=(bx + 8, meio_y)))
            bx_stats = bx + badge.get_width() + 16
        else:
            bx_stats = bx + 12

        # ── Stats à esquerda ─────────────────────────────────────────────────
        x = bx_stats
        x = self._stat(surface, x, meio_y, "$", str(coins), COLOR_GOLD)
        x = self._stat(surface, x + 18, meio_y, "Mortes", str(kills), COR_TEXTO)

        # Onda: valor branco + /total dim
        x += 18
        lbl_o = self._fonte_label.render("Onda", True, COR_LABEL_HUD)
        surface.blit(lbl_o, lbl_o.get_rect(midleft=(x, meio_y)))
        x += lbl_o.get_width() + 5
        onda_v = self._fonte_stat.render(str(wave), True, COR_TEXTO)
        surface.blit(onda_v, onda_v.get_rect(midleft=(x, meio_y)))
        x += onda_v.get_width()
        onda_t = self._fonte_label.render(f"/{total_waves}", True, COR_LABEL_HUD)
        surface.blit(onda_t, onda_t.get_rect(midleft=(x, meio_y)))
        x += onda_t.get_width() + 18

        # Tempo (ciano, sem label)
        if tempo_decorrido is not None and tempo_decorrido > 0:
            m = int(tempo_decorrido) // 60
            s = int(tempo_decorrido) % 60
            crono = self._fonte_stat.render(f"{m:02d}:{s:02d}", True, COR_CIANO)
            surface.blit(crono, crono.get_rect(midleft=(x, meio_y)))
            x += crono.get_width() + 18

        # Vidas (cor-coded)
        if lives > 6:
            cor_vida = COR_VIDA_OK
        elif lives >= 3:
            cor_vida = COR_VIDA_ALERTA
        else:
            cor_vida = COR_VIDA_CRITICA
        self._stat(surface, x, meio_y, "Vidas", str(lives), cor_vida)

        # ── Botões à direita ─────────────────────────────────────────────────
        mx, my = pygame.mouse.get_pos()

        ativo_2x = speed_multiplier >= 2.0
        self._botao_hud(
            surface, SPEED_BTN_RECT, "2x" if ativo_2x else "1x",
            ativo=ativo_2x, hover=SPEED_BTN_RECT.collidepoint(mx, my),
        )
        self._botao_hud(
            surface, AUTO_BTN_RECT, "AUTO",
            ativo=auto_skip, hover=AUTO_BTN_RECT.collidepoint(mx, my),
        )
        if skip_disponivel:
            self._botao_hud(
                surface, SKIP_BTN_RECT, f">> SKIP  +${skip_bonus}",
                ativo=False, skip=True,
                hover=SKIP_BTN_RECT.collidepoint(mx, my),
            )

        # ── Abaixo da barra: alerta de boss ou countdown ──────────────────────
        sub_y = by + TOP_BAR_HEIGHT + 14
        if boss_wave:
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                aviso = self._fonte_alert.render("!! BOSS !!", True, COR_BOSS_ALERTA)
                surface.blit(aviso, aviso.get_rect(center=(MAP_RECT.centerx, sub_y)))
        elif next_wave_in is not None:
            cd_txt = (
                f"Próxima onda: {next_wave_in:.0f}s"
                if not (modo_infinito and prox_boss_wave is not None)
                else f"Próxima onda: {next_wave_in:.0f}s  |  Boss: wave {prox_boss_wave}"
            )
            cd = self._fonte_cd.render(cd_txt, True, COR_CIANO)
            surface.blit(cd, cd.get_rect(center=(MAP_RECT.centerx, sub_y)))

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _stat(
        self,
        surface: pygame.Surface,
        x: int,
        meio_y: int,
        label: str,
        valor: str,
        cor_valor: tuple,
    ) -> int:
        """Desenha `label valor` inline; retorna o x após o bloco."""
        lbl = self._fonte_label.render(label, True, COR_LABEL_HUD)
        val = self._fonte_stat.render(valor, True, cor_valor)
        surface.blit(lbl, lbl.get_rect(midleft=(x, meio_y)))
        surface.blit(val, val.get_rect(midleft=(x + lbl.get_width() + 4, meio_y)))
        return x + lbl.get_width() + 4 + val.get_width()

    def _botao_hud(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        texto: str,
        ativo: bool = False,
        skip: bool = False,
        hover: bool = False,
    ) -> None:
        """Botão estilo btn-hud do HTML de referência."""
        if ativo:
            cor_bg    = COLOR_GOLD
            cor_borda = COLOR_GOLD
            cor_txt   = COR_BTN_HUD_ATIVO_TX
        elif skip:
            cor_bg    = COR_BTN_HUD_HOVER_BG if hover else COLOR_CARD_BG
            cor_borda = COR_VERDE_NEON
            cor_txt   = (5, 10, 0) if hover else COR_VERDE_NEON
        elif hover:
            cor_bg    = COR_BTN_HUD_HOVER_BG
            cor_borda = COLOR_GOLD
            cor_txt   = COLOR_GOLD
        else:
            cor_bg    = COLOR_CARD_BG
            cor_borda = COR_BORDA_SUTIL
            cor_txt   = COR_BTN_HUD_TEXTO

        pygame.draw.rect(surface, cor_bg, rect)
        pygame.draw.rect(surface, cor_borda, rect, 1)
        lbl = self._fonte_btn.render(texto, True, cor_txt)
        surface.blit(lbl, lbl.get_rect(center=rect.center))
