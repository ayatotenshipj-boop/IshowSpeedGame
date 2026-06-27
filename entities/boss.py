"""Boss final: Ancelotti.

Mecânicas:
- STUN: projéteis têm 30% de chance de stunná-lo por 1.5s (ICD 5s).
  Imune a stun nos primeiros 30s de combate.
- INVOCAÇÃO POR TIMER: spawna Labubu4 com 50% HP a cada 2.5s ao tomar dano.
  Em fase de fúria (HP < 30%): spawna a cada HIT.
- FASE DE FÚRIA: ao atingir 30% HP, velocidade +40%.
- REGENERAÇÃO PASSIVA: +15 HP/s quando é o único inimigo em campo.
- IMUNE A SLOW: apply_slow() é no-op.
"""

import logging
import random

import pygame

from entities.enemy import Enemy, Labubu4

logger = logging.getLogger(__name__)

# Tamanho do sprite do boss (maior que os 48×48 dos inimigos comuns).
BOSS_SPRITE_SIZE: int = 80
# Dimensões da barra de HP do boss.
HP_BAR_WIDTH: int = 70
HP_BAR_HEIGHT: int = 8


class Ancelotti(Enemy):
    """Boss com HP alto, imune a slow, stunável e que invoca reforços ao tomar dano."""

    name = "Ancelotti"
    max_hp = 3000
    speed = 65.0           # mais rápido que Labubu3 (50 px/s)
    reward = 300
    asset_name = "labubus/ancelotti"
    slow_immune = True
    damage_to_base = 5

    stun_chance: float = 0.30
    MUI_CHANCE: float = 0.15

    def __init__(self, assets, waypoints: list[dict]) -> None:
        super().__init__(assets, waypoints)
        self.stun_timer: float = 0.0
        self.stun_icd: float = 0.0
        self.mui_spawn_timer: float = 0.0
        self.stun_immune_timer: float = 30.0   # imune a stun nos primeiros 30s
        self._fury: bool = False                # fase de fúria (HP < 30%)
        self._speed_base: float = type(self).speed
        self.sprite = pygame.transform.smoothscale(
            assets.get(self.asset_name), (BOSS_SPRITE_SIZE, BOSS_SPRITE_SIZE)
        )
        self.fonte_nome = pygame.font.SysFont(None, 22)

    # ------------------------------------------------------------------ #
    # Movimento + stun + regen
    # ------------------------------------------------------------------ #
    def update(
        self, dt: float, waypoints: list[dict], enemies_count: int = 0
    ) -> tuple[bool, "Enemy | None"]:
        """Move; se stunnado, fica parado. Regenera HP quando sozinho no campo."""
        if self.stun_immune_timer > 0.0:
            self.stun_immune_timer -= dt

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            return (False, None)

        if self.stun_icd > 0.0:
            self.stun_icd -= dt
        if self.mui_spawn_timer > 0.0:
            self.mui_spawn_timer -= dt

        # Regeneração passiva: +15 HP/s quando sozinho em campo.
        if enemies_count == 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 15 * dt)

        reached_end = super().update(dt, waypoints)
        return (reached_end, None)

    def apply_stun(self, duration: float = 1.5) -> None:
        """Stun apenas se ICD zerou E imunidade inicial expirou."""
        if self.stun_icd <= 0.0 and self.stun_immune_timer <= 0.0:
            self.stun_timer = duration
            self.stun_icd = 5.0

    # ------------------------------------------------------------------ #
    # Dano + spawns
    # ------------------------------------------------------------------ #
    def receber_dano(
        self, dano: int, wave_atual: int, assets, waypoints: list[dict]
    ) -> "Labubu4 | None":
        """Aplica dano, ativa fúria a 30% HP e invoca Labubu4 por timer/hit."""
        self.hp -= dano

        if not self._fury and self.hp <= self.max_hp * 0.3:
            self._fury = True
            self.speed = self._speed_base * 1.4
            logger.debug("[Ancelotti] Fase de fúria ativada (HP=%d)", self.hp)

        pode_invocar = self.stun_timer <= 0.0
        if pode_invocar and (self._fury or self.mui_spawn_timer <= 0.0):
            spawn = self._criar_spawn(assets, waypoints)
            if not self._fury:
                self.mui_spawn_timer = 2.5
            return spawn
        return None

    def _criar_spawn(self, assets, waypoints: list[dict]) -> "Labubu4":
        """Cria Labubu4 com 50% HP, posição offsetada e levemente atrás no path."""
        spawn = Labubu4(assets, waypoints)
        spawn.max_hp = int(Labubu4.max_hp * 0.5)
        spawn.hp = spawn.max_hp
        spawn.reward = max(8, int(Labubu4.reward * 0.5))
        offset_x = random.choice([-48, -32, 32, 48])
        offset_y = random.choice([-32, 0, 32])
        spawn.x = self.x + offset_x
        spawn.y = self.y + offset_y
        spawn.waypoint_index = max(1, self.waypoint_index - 1)
        return spawn

    def apply_slow(self, duration: float = 2.0) -> None:
        """Imune a slow — ignora silenciosamente."""
        return

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Sprite grande (piscando amarelo se stunnado), barra de HP e nome."""
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
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
            txt = self.fonte_nome.render("ANCELOTTI", True, (230, 50, 50))
            surface.blit(txt, (int(self.x) - txt.get_width() // 2, bar_y - 20))
