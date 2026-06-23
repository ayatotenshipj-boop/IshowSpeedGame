"""Boss final: Ancelotti.

Extensão mínima de `Enemy`. Diferenças: muito HP, sprite maior, imune ao
efeito de slow do Speed4 e capaz de spawnar reforços (Labubu1) durante o
trajeto. O `update` retorna uma tupla (chegou_ao_fim, inimigo_spawnado|None),
diferente do `bool` dos inimigos normais — o game loop normaliza isso.
"""

import pygame

from entities.enemy import Enemy, Labubu1

# Tamanho do sprite do boss (maior que os 48×48 dos inimigos comuns).
BOSS_SPRITE_SIZE: int = 80
# Dimensões da barra de HP do boss.
HP_BAR_WIDTH: int = 70
HP_BAR_HEIGHT: int = 8


class Ancelotti(Enemy):
    """Boss com HP alto, imune a slow e que invoca reforços."""

    name = "Ancelotti"
    max_hp = 1500
    speed = 55.0          # levemente mais rápido que Labubu3 (50)
    reward = 200
    asset_name = "labubus/ancelotti"  # qualificada: há outro ancelotti.png em dialogs/
    slow_immune = True

    # Comportamento de invocação.
    spawn_cooldown: float = 8.0
    spawns_remaining: int = 4

    def __init__(self, assets, waypoints: list[dict]) -> None:
        super().__init__(assets, waypoints)
        self._assets = assets
        self.spawn_timer: float = 0.0
        # Sprite maior que o padrão.
        self.sprite = pygame.transform.smoothscale(
            assets.get(self.asset_name), (BOSS_SPRITE_SIZE, BOSS_SPRITE_SIZE)
        )

    # ------------------------------------------------------------------ #
    # Movimento + invocação
    # ------------------------------------------------------------------ #
    def update(self, dt: float, waypoints: list[dict]) -> tuple[bool, Enemy | None]:
        """Move e resolve a habilidade do boss (delega para `use_ability`).

        O game loop chama `update` em todos os inimigos; no boss ele encaminha
        para `use_ability`, mantendo o mesmo retorno em tupla.
        """
        return self.use_ability(dt, waypoints)

    def use_ability(self, dt: float, waypoints: list[dict]) -> tuple[bool, Enemy | None]:
        """Move e, periodicamente, invoca um Labubu1 na posição atual.

        Retorna (chegou_ao_fim, inimigo_spawnado_ou_None).
        """
        reached_end = super().update(dt, waypoints)

        spawned: Enemy | None = None
        if self.spawn_timer > 0.0:
            self.spawn_timer -= dt

        if self.spawn_timer <= 0.0 and self.spawns_remaining > 0:
            self.spawn_timer = self.spawn_cooldown
            self.spawns_remaining -= 1
            # Reforço começa na posição atual do boss e segue de onde ele está.
            reforco = Labubu1(self._assets, waypoints)
            reforco.x = self.x
            reforco.y = self.y
            reforco.waypoint_index = self.waypoint_index
            spawned = reforco

        return reached_end, spawned

    def apply_slow(self, duration: float = 2.0) -> None:
        """Imune a slow — ignora silenciosamente."""
        return

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Sprite grande, barra de HP larga e nome em vermelho."""
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
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
