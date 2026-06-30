"""Gerenciador de waves para o Modo Impossível.

Spawna IMP_ANCELOTTI_COUNT Ancelottis com velocidade IMP_ANCELOTTI_SPEED
em sequência, um a cada IMP_ANCELOTTI_INTERVAL segundos.
Quando todos morreram → is_finished() = True → vitória.
"""

import logging

from config.settings import (
    IMP_ANCELOTTI_COUNT,
    IMP_ANCELOTTI_INTERVAL,
    IMP_ANCELOTTI_SPEED,
    INF_INTERVAL,
)
from entities.boss import Ancelotti
from entities.enemy import Enemy
from entities.wave_manager import WaveManager

logger = logging.getLogger(__name__)


class ImpossibleWaveManager(WaveManager):
    """100 Ancelottis com speed 20, um de cada vez."""

    def __init__(self) -> None:
        super().__init__()
        self._spawned: int = 0
        self._done: bool = False

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def is_finished(self) -> bool:
        return self._done

    def display_wave(self) -> int:
        """Retorna quantos Ancelottis já foram spawnados (1-indexed)."""
        return max(1, self._spawned)

    # ------------------------------------------------------------------ #
    # Atualização
    # ------------------------------------------------------------------ #
    def update(self, dt: float, enemies: list[Enemy], waypoints: list[dict]) -> None:
        if self._done:
            return
        if self.wave_active:
            self._spawnar(dt, enemies, waypoints)
        else:
            self.wave_timer -= dt
            if self.wave_timer <= 0.0:
                self._iniciar_onda()

    def _iniciar_onda(self) -> None:
        self.spawn_queue = [
            {"type": "ancelotti", "interval": IMP_ANCELOTTI_INTERVAL}
            for _ in range(IMP_ANCELOTTI_COUNT)
        ]
        self.spawn_timer = 0.0
        self.wave_active = True
        logger.info(
            "[Impossível] Iniciando — %d Ancelottis, speed %.1f.",
            IMP_ANCELOTTI_COUNT,
            IMP_ANCELOTTI_SPEED,
        )

    def _spawnar(self, dt: float, enemies: list[Enemy], waypoints: list[dict]) -> None:
        self.spawn_timer -= dt
        while self.spawn_queue and self.spawn_timer <= 0.0:
            self.spawn_queue.pop(0)
            inimigo = Ancelotti(self.assets, waypoints)
            inimigo.speed = IMP_ANCELOTTI_SPEED
            inimigo._speed_base = IMP_ANCELOTTI_SPEED
            enemies.append(inimigo)
            self._spawned += 1
            self.spawn_timer += IMP_ANCELOTTI_INTERVAL
            logger.debug("[Impossível] Ancelotti #%d spawnado.", self._spawned)

        if not self.spawn_queue and not enemies:
            self._done = True
            self.wave_active = False
            logger.info("[Impossível] Todos os 100 Ancelottis derrotados!")
