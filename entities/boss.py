"""Boss final: Ancelotti.

Mecânicas:
- STUN: projéteis têm 30% de chance de stunná-lo por 1.5s (ICD 5s).
  Imune a stun nos primeiros 30s de combate.
- INVOCAÇÃO POR TIMER: a cada SPAWN_INTERVAL segundos, 50% de chance de
  invocar 3 Labubu4s ligeiramente à frente dele no path.
- FASE DE FÚRIA: ao atingir 30% HP, velocidade +40%.
- REGENERAÇÃO PASSIVA: +15 HP/s quando é o único inimigo em campo.
- IMUNE A SLOW: apply_slow() é no-op.
"""

import logging
import random

import pygame

from entities.enemy import Enemy, Labubu4

logger = logging.getLogger(__name__)

BOSS_SPRITE_SIZE: int = 80
HP_BAR_WIDTH: int = 70
HP_BAR_HEIGHT: int = 8

# Invocação de reforços.
SPAWN_INTERVAL: float = 8.0   # segundos entre tentativas
SPAWN_CHANCE: float = 0.50    # probabilidade por tentativa
SPAWN_COUNT: int = 3          # labubus por invocação bem-sucedida
SPAWN_WAYPOINTS_AHEAD: int = 2  # waypoints à frente de Ancelotti


class Ancelotti(Enemy):
    """Boss com HP alto, imune a slow, stunável e que invoca reforços por timer."""

    name = "Ancelotti"
    max_hp = 3000
    speed = 65.0
    reward = 300
    asset_name = "labubus/ancelotti"
    slow_immune = True
    damage_to_base = 5

    stun_chance: float = 0.30

    def __init__(self, assets, waypoints: list[dict]) -> None:
        super().__init__(assets, waypoints)
        self._assets = assets
        self._waypoints = waypoints

        self.stun_timer: float = 0.0
        self.stun_icd: float = 0.0
        self.stun_immune_timer: float = 30.0
        self._fury: bool = False
        self._speed_base: float = type(self).speed
        self._spawn_timer: float = SPAWN_INTERVAL

        self.sprite = pygame.transform.smoothscale(
            assets.get(self.asset_name), (BOSS_SPRITE_SIZE, BOSS_SPRITE_SIZE)
        )
        self.fonte_nome = pygame.font.SysFont(None, 22)

    # ------------------------------------------------------------------ #
    # Movimento + stun + regen + spawn
    # ------------------------------------------------------------------ #
    def update(
        self, dt: float, waypoints: list[dict], enemies_count: int = 0
    ) -> tuple[bool, "list[Labubu4] | None"]:
        """Move, stuna, regenera e tenta invocar reforços a cada SPAWN_INTERVAL s."""
        if self.stun_immune_timer > 0.0:
            self.stun_immune_timer -= dt

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            return (False, None)

        if self.stun_icd > 0.0:
            self.stun_icd -= dt

        # Regeneração passiva: +15 HP/s quando sozinho em campo.
        if enemies_count == 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 15 * dt)

        # Timer de invocação.
        spawns: list[Labubu4] | None = None
        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            self._spawn_timer = SPAWN_INTERVAL
            if random.random() < SPAWN_CHANCE:
                spawns = self._criar_grupo_spawn()

        reached_end = super().update(dt, waypoints)
        return (reached_end, spawns)

    def apply_stun(self, duration: float = 1.5) -> None:
        if self.stun_icd <= 0.0 and self.stun_immune_timer <= 0.0:
            self.stun_timer = duration
            self.stun_icd = 5.0

    # ------------------------------------------------------------------ #
    # Dano + fúria
    # ------------------------------------------------------------------ #
    def receber_dano(self, dano: int, wave_atual: int) -> None:
        """Aplica dano e ativa fúria a 30% HP."""
        self.hp -= dano

        if not self._fury and self.hp <= self.max_hp * 0.3:
            self._fury = True
            self.speed = self._speed_base * 1.4
            logger.debug("[Ancelotti] Fase de fúria ativada (HP=%d)", self.hp)

    # ------------------------------------------------------------------ #
    # Invocação
    # ------------------------------------------------------------------ #
    def _criar_grupo_spawn(self) -> list[Labubu4]:
        """Cria SPAWN_COUNT Labubu4s com 50% HP levemente à frente de Ancelotti."""
        wp = self._waypoints
        grupo: list[Labubu4] = []
        wi_target = min(self.waypoint_index + SPAWN_WAYPOINTS_AHEAD, len(wp) - 1)
        wi_pos = max(0, wi_target - 1)
        base_x = float(wp[wi_pos]["x"])
        base_y = float(wp[wi_pos]["y"])

        for _ in range(SPAWN_COUNT):
            spawn = Labubu4(self._assets, wp)
            spawn.max_hp = int(Labubu4.max_hp * 0.5)
            spawn.hp = spawn.max_hp
            spawn.reward = max(8, int(Labubu4.reward * 0.5))
            spawn.waypoint_index = wi_target
            spawn.x = base_x + random.uniform(-24, 24)
            spawn.y = base_y + random.uniform(-24, 24)
            grupo.append(spawn)

        logger.info(
            "[Ancelotti] Invocou %d Labubu4s (waypoint %d → %d).",
            SPAWN_COUNT, self.waypoint_index, wi_target,
        )
        return grupo

    def apply_slow(self, duration: float = 2.0) -> None:
        return

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
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
