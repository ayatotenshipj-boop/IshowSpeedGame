"""Gerenciador de waves para o Modo Infinito.

Herda de WaveManager e sobrescreve a geração de ondas: ao invés de WAVES
fixas, cada onda é gerada proceduralmente via wave_scaler. Nunca termina
(is_finished sempre False). Boss a cada INF_BOSS_WAVE_INTERVAL waves.
"""

import logging

from config.settings import INF_ANUNCIO_DURATION, INF_BOSS_WAVE_INTERVAL, INF_INTERVAL
from entities.boss import Ancelotti
from entities.enemy import Enemy
from entities.wave_manager import TIPOS, WaveManager
from entities.wave_scaler import (
    calcular_hp_boss,
    calcular_hp_inimigo,
    calcular_quantidade_inimigos,
    calcular_recompensa_kill,
    calcular_velocidade_inimigo,
    e_boss_wave,
    escolher_tipos_wave,
    intervalo_spawn,
)

logger = logging.getLogger(__name__)


class InfiniteWaveManager(WaveManager):
    """Waves infinitas com scaling procedural e boss a cada N waves."""

    def __init__(self) -> None:
        super().__init__()
        # Anuncia a wave com um banner por INF_ANUNCIO_DURATION segundos.
        self._anuncio_timer: float = 0.0
        self._anuncio_wave_num: int = 0

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    @property
    def anuncio_ativo(self) -> bool:
        """True enquanto o banner de wave está sendo exibido."""
        return self._anuncio_timer > 0.0

    @property
    def anuncio_wave_num(self) -> int:
        """Número da wave anunciada (1-indexed)."""
        return self._anuncio_wave_num

    def proxima_boss_wave(self, wave_atual: int) -> int:
        """Retorna o número da próxima boss wave a partir de wave_atual."""
        n = (wave_atual // INF_BOSS_WAVE_INTERVAL + 1) * INF_BOSS_WAVE_INTERVAL
        return n

    def is_finished(self) -> bool:
        """Infinito nunca termina."""
        return False

    def display_wave(self) -> int:
        """Número da wave atual (1-indexed)."""
        return self.current_wave + 1

    # ------------------------------------------------------------------ #
    # Atualização
    # ------------------------------------------------------------------ #
    def update(self, dt: float, enemies: list[Enemy], waypoints: list[dict]) -> None:
        """Avança a temporização e spawna inimigos; sempre inicia próxima wave."""
        self._enemies_ref = enemies

        if self._anuncio_timer > 0.0:
            self._anuncio_timer -= dt

        if self.wave_active:
            self._spawnar(dt, enemies, waypoints)
        else:
            self.wave_timer -= dt
            if self.wave_timer <= 0.0:
                self._iniciar_onda()

    def _iniciar_onda(self) -> None:
        """Gera fila de spawns para a wave atual via wave_scaler."""
        wave_num = self.current_wave + 1  # 1-indexed
        tipos = escolher_tipos_wave(wave_num)
        qtd = calcular_quantidade_inimigos(wave_num)
        itvl = intervalo_spawn(wave_num)

        self.spawn_queue = []
        for i in range(qtd):
            tipo = tipos[i % len(tipos)]
            self.spawn_queue.append({"type": tipo, "interval": itvl})

        # Boss wave: insere Ancelotti no meio da fila de spawn.
        if e_boss_wave(wave_num):
            meio = len(self.spawn_queue) // 2
            self.spawn_queue.insert(meio, {"type": "ancelotti", "interval": 2.0})
            logger.info("[Infinito] Boss wave %d — Ancelotti spawn no índice %d.", wave_num, meio)

        self.spawn_timer = 0.0
        self.wave_active = True
        self._anuncio_timer = INF_ANUNCIO_DURATION
        self._anuncio_wave_num = wave_num
        logger.info("[Infinito] Wave %d iniciada (%d inimigos).", wave_num, len(self.spawn_queue))

    def _spawnar(self, dt: float, enemies: list[Enemy], waypoints: list[dict]) -> None:
        """Aplica scaling de HP/velocidade/recompensa por wave ao spawnar."""
        self.spawn_timer -= dt
        wave_num = self.current_wave + 1  # wave sendo spawnada agora

        while self.spawn_queue and self.spawn_timer <= 0.0:
            spawn = self.spawn_queue.pop(0)
            is_boss = spawn["type"] == "ancelotti"
            classe = TIPOS[spawn["type"]]
            inimigo = classe(self.assets, waypoints)

            if is_boss:
                hp_boss = calcular_hp_boss(type(inimigo).max_hp, wave_num)
                inimigo.max_hp = round(hp_boss)
                inimigo.hp = inimigo.max_hp
                # Boss também fica um pouco mais rápido, mas cap menor (wave 30).
                inimigo.speed = calcular_velocidade_inimigo(
                    type(inimigo).speed, min(wave_num, 30)
                )
                if hasattr(inimigo, "_speed_base"):
                    inimigo._speed_base = inimigo.speed
                # Passa a wave atual para o boss escalar reforços corretamente.
                inimigo._wave_num = wave_num
            else:
                base_hp = type(inimigo).max_hp
                inimigo.max_hp = round(calcular_hp_inimigo(base_hp, wave_num))
                inimigo.hp = inimigo.max_hp
                inimigo.speed = calcular_velocidade_inimigo(type(inimigo).speed, wave_num)
                if hasattr(inimigo, "velocidade_base"):
                    inimigo.velocidade_base = inimigo.speed
                inimigo.reward = calcular_recompensa_kill(type(inimigo).reward, wave_num)

            enemies.append(inimigo)
            self.spawn_timer += spawn["interval"]

        # Só encerra a wave quando spawn acabou E todos os inimigos morreram.
        if not self.spawn_queue and not enemies:
            self.wave_active = False
            self.current_wave += 1
            self.wave_timer = INF_INTERVAL
