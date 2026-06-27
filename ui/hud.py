"""HUD do jogo (barra superior com moedas, onda e vida).

Camada de UI em Pygame puro (sem pygame_gui). Desenha uma faixa no topo da
área do mapa com o saldo, a onda atual e as vidas (cor varia com o valor).
"""

import pygame

from config.settings import (
    COLOR_GOLD, COR_TEXTO, MAP_RECT,
    COR_CIANO, COR_VIDA_OK, COR_VIDA_ALERTA, COR_VIDA_CRITICA,
    COR_BARRA_HUD_TOPO, COR_LABEL_HUD,
    COR_BTN_FUNDO, COR_BTN_INATIVO, COR_BTN_TEXTO_INATIVO,
    COR_BTN_ATIVO, COR_BTN_TEXTO_ATIVO, COR_BTN_SPEED_ESCURO,
    COR_SKIP_FUNDO, COR_SKIP_BORDA, COR_SKIP_TEXTO, COR_BOSS_ALERTA,
)

# Altura da faixa do HUD no topo do mapa.
TOP_BAR_HEIGHT: int = 30

# Botões interativos do HUD (posições fixas no espaço de render).
SPEED_BTN_RECT: pygame.Rect = pygame.Rect(
    MAP_RECT.right - 90, MAP_RECT.y + TOP_BAR_HEIGHT + 8, 74, 30
)
# Botão Auto-Skip (toggle), logo abaixo do botão de velocidade.
AUTO_BTN_RECT: pygame.Rect = pygame.Rect(
    MAP_RECT.right - 90, MAP_RECT.y + TOP_BAR_HEIGHT + 44, 74, 30
)
SKIP_BTN_RECT: pygame.Rect = pygame.Rect(
    MAP_RECT.centerx - 110, MAP_RECT.y + TOP_BAR_HEIGHT + 34, 220, 32
)


class HUD:
    """Barra superior de informações da partida."""

    def __init__(self) -> None:
        self._fonte = pygame.font.SysFont("monospace", 23)
        self._fonte_pequena = pygame.font.SysFont("monospace", 20)
        self._fonte_btn = pygame.font.SysFont(None, 22, bold=True)
        # Surface cacheada — tamanho fixo, criada uma vez
        self._barra_topo = pygame.Surface((MAP_RECT.width, TOP_BAR_HEIGHT), pygame.SRCALPHA)
        self._barra_topo.fill(COR_BARRA_HUD_TOPO)

    # ------------------------------------------------------------------ #
    # Botões (rects fixos; lógica de clique fica no main)
    # ------------------------------------------------------------------ #
    @staticmethod
    def speed_button_rect() -> pygame.Rect:
        """Rect do botão de velocidade (2×)."""
        return SPEED_BTN_RECT

    @staticmethod
    def skip_button_rect() -> pygame.Rect:
        """Rect do botão de pular onda (válido só quando o Skip está disponível)."""
        return SKIP_BTN_RECT

    @staticmethod
    def auto_button_rect() -> pygame.Rect:
        """Rect do botão Auto-Skip (toggle, sempre clicável durante o jogo)."""
        return AUTO_BTN_RECT

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
    ) -> None:
        """Desenha a faixa superior (moedas à esquerda, onda no centro, vidas à direita)."""
        # Fundo da faixa (Surface cacheada em __init__).
        surface.blit(self._barra_topo, (MAP_RECT.x, MAP_RECT.y))

        meio_y = MAP_RECT.y + TOP_BAR_HEIGHT // 2

        # Esquerda: $ valor (dourado) + label "Mortes:" dim + valor branco.
        moedas_val = self._fonte.render(f"$ {coins}", True, COLOR_GOLD)
        surface.blit(moedas_val, (MAP_RECT.x + 16, meio_y - moedas_val.get_height() // 2))
        x_mortes = MAP_RECT.x + 16 + moedas_val.get_width() + 18
        lbl_mortes = self._fonte_pequena.render("Mortes:", True, COR_LABEL_HUD)
        surface.blit(lbl_mortes, (x_mortes, meio_y - lbl_mortes.get_height() // 2))
        val_mortes = self._fonte.render(str(kills), True, COR_TEXTO)
        surface.blit(val_mortes, (x_mortes + lbl_mortes.get_width() + 4, meio_y - val_mortes.get_height() // 2))

        # Centro: "Onda" dim + "wave/total" branco.
        lbl_onda = self._fonte_pequena.render("Onda", True, COR_LABEL_HUD)
        val_onda = self._fonte.render(f"{wave} / {total_waves}", True, COR_TEXTO)
        bloco_w = lbl_onda.get_width() + 5 + val_onda.get_width()
        bx = MAP_RECT.centerx - bloco_w // 2
        surface.blit(lbl_onda, (bx, meio_y - lbl_onda.get_height() // 2))
        surface.blit(val_onda, (bx + lbl_onda.get_width() + 5, meio_y - val_onda.get_height() // 2))

        # Direita: "Vidas:" dim + valor cor-coded.
        if lives > 6:
            cor_vida = COR_VIDA_OK
        elif lives >= 3:
            cor_vida = COR_VIDA_ALERTA
        else:
            cor_vida = COR_VIDA_CRITICA
        val_vidas = self._fonte.render(str(lives), True, cor_vida)
        lbl_vidas = self._fonte_pequena.render("Vidas:", True, COR_LABEL_HUD)
        x_vidas = MAP_RECT.right - val_vidas.get_width() - lbl_vidas.get_width() - 20
        surface.blit(lbl_vidas, (x_vidas, meio_y - lbl_vidas.get_height() // 2))
        surface.blit(val_vidas, (x_vidas + lbl_vidas.get_width() + 4, meio_y - val_vidas.get_height() // 2))

        # Abaixo do centro: contagem regressiva (ciano) ou aviso de boss (vermelho piscante).
        if boss_wave:
            # Pisca: alterna visível/oculto a cada 0.5s.
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                aviso = self._fonte.render("!! BOSS !!", True, COR_BOSS_ALERTA)
                surface.blit(
                    aviso,
                    aviso.get_rect(
                        center=(MAP_RECT.centerx, MAP_RECT.y + TOP_BAR_HEIGHT + 16)
                    ),
                )
        elif next_wave_in is not None:
            aviso = self._fonte_pequena.render(
                f"Próxima onda: {next_wave_in:.0f}s", True, COR_CIANO
            )
            surface.blit(
                aviso,
                aviso.get_rect(center=(MAP_RECT.centerx, MAP_RECT.y + TOP_BAR_HEIGHT + 14)),
            )

        # Skip durante a wave: só aparece quando disponível (15–20s após o
        # início), com o bônus de moedas calculado no chamador.
        if skip_disponivel:
            self._desenhar_botao_skip(surface, skip_bonus)

        # Botões de velocidade (2×) e Auto-Skip — sempre durante o jogo.
        self._desenhar_botao_speed(surface, speed_multiplier)
        self._desenhar_botao_auto(surface, auto_skip)

        # Cronômetro da partida (canto direito, ABAIXO do botão Auto-Skip para
        # não sobrepô-lo — Bloco 7, v1.2.1; antes colidia com o AUTO_BTN_RECT).
        if tempo_decorrido is not None and tempo_decorrido > 0:
            m = int(tempo_decorrido) // 60
            s = int(tempo_decorrido) % 60
            crono = self._fonte.render(f"{m:02d}:{s:02d}", True, COR_CIANO)
            surface.blit(
                crono,
                crono.get_rect(topright=(MAP_RECT.right - 16, AUTO_BTN_RECT.bottom + 8)),
            )

    def _desenhar_botao_skip(self, surface: pygame.Surface, bonus: int) -> None:
        """Desenha o botão [⏩ SKIP +$bonus]."""
        rect = SKIP_BTN_RECT
        pygame.draw.rect(surface, COR_SKIP_FUNDO, rect, border_radius=6)
        pygame.draw.rect(surface, COR_SKIP_BORDA, rect, 2, border_radius=6)
        txt = self._fonte_btn.render(f">> SKIP  +${bonus}", True, COR_SKIP_TEXTO)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _desenhar_botao_auto(self, surface: pygame.Surface, ativo: bool) -> None:
        """Desenha o toggle [AUTO]: cinza (desativo) / verde (ativo)."""
        rect = AUTO_BTN_RECT
        cor_borda = COR_BTN_ATIVO if ativo else COR_BTN_INATIVO
        cor_txt = COR_BTN_TEXTO_ATIVO if ativo else COR_BTN_TEXTO_INATIVO
        pygame.draw.rect(surface, COR_BTN_FUNDO, rect, border_radius=6)
        pygame.draw.rect(surface, cor_borda, rect, 2, border_radius=6)
        txt = self._fonte_btn.render("AUTO", True, cor_txt)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _desenhar_botao_speed(self, surface: pygame.Surface, mult: float) -> None:
        """Desenha o botão de velocidade: [1×] cinza ou [2×] dourado piscante."""
        rect = SPEED_BTN_RECT
        ativo = mult >= 2.0
        if ativo:
            piscar = (pygame.time.get_ticks() // 400) % 2 == 0
            cor_borda = COLOR_GOLD if piscar else COR_BTN_SPEED_ESCURO
            cor_txt = COLOR_GOLD
            label = "2x"
        else:
            cor_borda = COR_BTN_INATIVO
            cor_txt = COR_BTN_TEXTO_INATIVO
            label = "1x"
        pygame.draw.rect(surface, COR_BTN_FUNDO, rect, border_radius=6)
        pygame.draw.rect(surface, cor_borda, rect, 2, border_radius=6)
        txt = self._fonte_btn.render(label, True, cor_txt)
        surface.blit(txt, txt.get_rect(center=rect.center))
