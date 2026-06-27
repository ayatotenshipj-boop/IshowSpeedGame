"""Boss final: Ancelotti.

Extensão mínima de `Enemy`. Diferenças: muito HP, sprite maior, imune ao
efeito de slow do Speed4, e mecânicas próprias da v1.2.0:

- STUN: qualquer projétil tem 15% de chance de stunná-lo por 1.5s. Stunnado,
  ele para de se mover e não invoca reforços.
- INVOCAÇÃO POR DANO: ao tomar dano (não mais por cooldown de tempo), tem 20%
  de chance de invocar um `LabubuMUI` (reforço 50% mais fraco) — exceto durante
  o stun.

O `update` retorna uma tupla (chegou_ao_fim, inimigo_spawnado|None), mantendo o
contrato do game loop. Com a invocação migrada para `receber_dano`, o segundo
elemento é sempre None aqui (o game loop normaliza tupla vs. bool).
"""

import random

import pygame

from entities.enemy import Enemy, LabubuMUI, criar_mui

# Tamanho do sprite do boss (maior que os 48×48 dos inimigos comuns).
BOSS_SPRITE_SIZE: int = 80
# Dimensões da barra de HP do boss.
HP_BAR_WIDTH: int = 70
HP_BAR_HEIGHT: int = 8


class Ancelotti(Enemy):
    """Boss com HP alto, imune a slow, stunável e que invoca MUI ao tomar dano."""

    name = "Ancelotti"
    max_hp = 1500
    speed = 55.0          # levemente mais rápido que Labubu3 (50)
    reward = 300          # v1.2.1 (era 200)
    asset_name = "labubus/ancelotti"  # qualificada: há outro ancelotti.png em dialogs/
    slow_immune = True
    damage_to_base = 5    # quase game over instantâneo se chegar ao fim

    # Mecânicas v1.2.0.
    stun_chance: float = 0.15      # chance de stun por projétil acertado
    MUI_CHANCE: float = 0.20       # chance de invocar Labubu MUI ao tomar dano

    def __init__(self, assets, waypoints: list[dict]) -> None:
        super().__init__(assets, waypoints)
        self.stun_timer: float = 0.0
        self.stun_icd: float = 0.0      # NOVO: Cooldown interno para não permar stunnar
        self.mui_spawn_timer: float = 0.0 # NOVO: Timer para limitar invocação de MUI
        # Sprite maior que o padrão.
        self.sprite = pygame.transform.smoothscale(
            assets.get(self.asset_name), (BOSS_SPRITE_SIZE, BOSS_SPRITE_SIZE)
        )

    # ------------------------------------------------------------------ #
    # Movimento + stun
    # ------------------------------------------------------------------ #
    def update(self, dt: float, waypoints: list[dict]) -> tuple[bool, Enemy | None]:
        """Move; se stunnado, fica parado. Mantém o retorno em tupla."""
        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            return (False, None)  # parado durante o stun
        
        # Atualiza cooldowns internos
        if self.stun_icd > 0.0:
            self.stun_icd -= dt
        if self.mui_spawn_timer > 0.0:
            self.mui_spawn_timer -= dt

        reached_end = super().update(dt, waypoints)
        return (reached_end, None)

    def apply_stun(self, duration: float = 1.5) -> None:
        """Aplica stun por `duration` segundos apenas se o ICD tiver zerado."""
        if self.stun_icd <= 0.0:
            self.stun_timer = duration
            self.stun_icd = 5.0  # 5 segundos de imunidade a novo stun

    def receber_dano(
        self, dano: int, wave_atual: int, assets, waypoints: list[dict]
    ) -> "LabubuMUI | None":
        """Aplica `dano` e, baseado em timer, invoca um Labubu MUI."""
        self.hp -= dano
        # Invoca um MUI a cada 2.5s, se não estiver stunnado e o timer zerou
        if self.stun_timer <= 0.0 and self.mui_spawn_timer <= 0.0:
            mui = criar_mui(assets, waypoints, wave_atual)
            mui.x, mui.y = self.x, self.y
            mui.waypoint_index = self.waypoint_index
            self.mui_spawn_timer = 2.5  # só invoca outro daqui 2.5 segundos
            return mui
        return None

    def apply_slow(self, duration: float = 2.0) -> None:
        """Imune a slow — ignora silenciosamente."""
        return

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Sprite grande (piscando amarelo se stunnado), barra de HP e nome."""
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        # Durante o stun, o sprite pisca amarelo.
        if self.stun_timer > 0.0 and (pygame.time.get_ticks() // 120) % 2 == 0:
            flash = self.sprite.copy()
            flash.fill((255, 255, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(flash, rect)
        else:
            surface.blit(self.sprite, rect)

        if self.hp < self.max_hp:
            bar_x = int(self.x) - HP_BAR_WIDTH // 2
            bar_y = rect.top - 6 - HP_BAR_HEIGHT
            pygame.draw.rect(
                surface, (180, 40, 40), (bar_x, bar_y, HP_BAR_WIDTH, HP_BAR_HEIGHT)
            )
            frac = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(
                surface,
                (60, 200, 70),
                (bar_x, bar_y, int(HP_BAR_WIDTH * frac), HP_BAR_HEIGHT),
            )
            # Nome acima da barra.
            fonte = pygame.font.SysFont(None, 22)
            txt = fonte.render("ANCELOTTI", True, (230, 50, 50))
            surface.blit(txt, (int(self.x) - txt.get_width() // 2, bar_y - 20))
