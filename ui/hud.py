"""HUD do jogo (barra superior com moedas, onda e vida).

Camada de UI em Pygame puro (sem pygame_gui). Desenha uma faixa no topo da
área do mapa com o saldo, a onda atual e as vidas (cor varia com o valor).
"""

import pygame

from config.settings import COLOR_GOLD, COR_TEXTO, MAP_RECT

# Altura da faixa do HUD no topo do mapa.
TOP_BAR_HEIGHT: int = 30
# Cores das vidas conforme a quantidade.
COR_VIDA_OK: tuple[int, int, int] = (80, 220, 90)       # > 10
COR_VIDA_ALERTA: tuple[int, int, int] = (240, 210, 60)  # 5-10
COR_VIDA_CRITICA: tuple[int, int, int] = (220, 60, 60)  # < 5
COR_CIANO: tuple[int, int, int] = (80, 220, 230)

# Botões interativos do HUD (posições fixas no espaço de render).
SPEED_BTN_RECT: pygame.Rect = pygame.Rect(
    MAP_RECT.right - 90, MAP_RECT.y + TOP_BAR_HEIGHT + 8, 74, 30
)
SKIP_BTN_RECT: pygame.Rect = pygame.Rect(
    MAP_RECT.centerx - 110, MAP_RECT.y + TOP_BAR_HEIGHT + 34, 220, 32
)


class HUD:
    """Barra superior de informações da partida."""

    def __init__(self) -> None:
        self._fonte = pygame.font.SysFont(None, 26)
        self._fonte_pequena = pygame.font.SysFont(None, 22)
        self._fonte_btn = pygame.font.SysFont(None, 22, bold=True)

    # ------------------------------------------------------------------ #
    # Botões (rects fixos; lógica de clique fica no main)
    # ------------------------------------------------------------------ #
    @staticmethod
    def speed_button_rect() -> pygame.Rect:
        """Rect do botão de velocidade (2×)."""
        return SPEED_BTN_RECT

    @staticmethod
    def skip_button_rect() -> pygame.Rect:
        """Rect do botão de pular onda (válido só enquanto há intervalo)."""
        return SKIP_BTN_RECT

    @staticmethod
    def skip_bonus(next_wave_in: float | None) -> int:
        """Bônus de moedas por pular: 3 por segundo restante."""
        if next_wave_in is None:
            return 0
        return int(next_wave_in * 3)

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
    ) -> None:
        """Desenha a faixa superior (moedas à esquerda, onda no centro, vidas à direita)."""
        # Fundo da faixa.
        barra = pygame.Surface((MAP_RECT.width, TOP_BAR_HEIGHT), pygame.SRCALPHA)
        barra.fill((10, 10, 20, 170))
        surface.blit(barra, (MAP_RECT.x, MAP_RECT.y))

        meio_y = MAP_RECT.y + TOP_BAR_HEIGHT // 2

        # Esquerda: moedas (dourado) e contador de mortes (branco).
        moedas = self._fonte.render(f"$ {coins}", True, COLOR_GOLD)
        surface.blit(moedas, (MAP_RECT.x + 16, meio_y - moedas.get_height() // 2))
        mortes = self._fonte.render(f"Mortes: {kills}", True, COR_TEXTO)
        surface.blit(
            mortes,
            (MAP_RECT.x + 16 + moedas.get_width() + 24, meio_y - mortes.get_height() // 2),
        )

        # Centro: onda atual.
        onda = self._fonte.render(f"Onda {wave} / {total_waves}", True, COR_TEXTO)
        surface.blit(onda, onda.get_rect(center=(MAP_RECT.centerx, meio_y)))

        # Direita: vidas (cor conforme valor).
        if lives > 10:
            cor = COR_VIDA_OK
        elif lives >= 5:
            cor = COR_VIDA_ALERTA
        else:
            cor = COR_VIDA_CRITICA
        vidas = self._fonte.render(f"Vidas: {lives}", True, cor)
        surface.blit(
            vidas,
            (MAP_RECT.right - vidas.get_width() - 16, meio_y - vidas.get_height() // 2),
        )

        # Abaixo do centro: contagem regressiva (ciano) ou aviso de boss (vermelho piscante).
        if boss_wave:
            # Pisca: alterna visível/oculto a cada 0.5s.
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                aviso = self._fonte.render("!! BOSS !!", True, (230, 50, 50))
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
            # Botão de pular onda com bônus de moedas (3/seg restante).
            self._desenhar_botao_skip(surface, self.skip_bonus(next_wave_in))

        # Botão de velocidade (2×) — sempre disponível durante o jogo.
        self._desenhar_botao_speed(surface, speed_multiplier)

    def _desenhar_botao_skip(self, surface: pygame.Surface, bonus: int) -> None:
        """Desenha o botão [⏩ SKIP +$bonus]."""
        rect = SKIP_BTN_RECT
        pygame.draw.rect(surface, (40, 90, 50), rect, border_radius=6)
        pygame.draw.rect(surface, (90, 220, 110), rect, 2, border_radius=6)
        txt = self._fonte_btn.render(f">> SKIP  +${bonus}", True, (220, 255, 220))
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _desenhar_botao_speed(self, surface: pygame.Surface, mult: float) -> None:
        """Desenha o botão de velocidade: [1×] cinza ou [2×] dourado piscante."""
        rect = SPEED_BTN_RECT
        ativo = mult >= 2.0
        if ativo:
            piscar = (pygame.time.get_ticks() // 400) % 2 == 0
            cor_borda = COLOR_GOLD if piscar else (150, 120, 30)
            cor_txt = COLOR_GOLD
            label = "2x"
        else:
            cor_borda = (120, 120, 130)
            cor_txt = (180, 180, 190)
            label = "1x"
        pygame.draw.rect(surface, (30, 30, 45), rect, border_radius=6)
        pygame.draw.rect(surface, cor_borda, rect, 2, border_radius=6)
        txt = self._fonte_btn.render(label, True, cor_txt)
        surface.blit(txt, txt.get_rect(center=rect.center))
