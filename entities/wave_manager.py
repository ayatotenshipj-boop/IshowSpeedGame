"""Controle de ondas de inimigos.

Spawna os Labubus de cada onda em intervalos definidos, com um tempo de espera
entre ondas. O primeiro inimigo da partida só aparece após um pequeno atraso
inicial. Toda a temporização é baseada em delta-time.
"""

from config.settings import MODOS_DIFICULDADE
from entities.boss import Ancelotti
from entities.enemy import ENEMY_TYPES, Enemy

# Mapa de tipos usado para instanciar inimigos (inimigos comuns + boss).
TIPOS: dict[str, type[Enemy]] = {**ENEMY_TYPES, "ancelotti": Ancelotti}

# Definição das ondas. Cada onda é uma lista de grupos de spawn.
# São 15 ondas no total; o boss (Ancelotti) aparece na última (onda 15).
WAVES: list[list[dict]] = [
    # Onda 1 — introdução
    [{"type": "labubu1", "count": 5, "interval": 1.5}],
    # Onda 2
    [{"type": "labubu1", "count": 6, "interval": 1.2},
     {"type": "labubu2", "count": 2, "interval": 2.0}],
    # Onda 3
    [{"type": "labubu2", "count": 4, "interval": 1.5},
     {"type": "labubu3", "count": 2, "interval": 3.0}],
    # Onda 4
    [{"type": "labubu3", "count": 3, "interval": 2.5},
     {"type": "labubu4", "count": 3, "interval": 1.8}],
    # Onda 5
    [{"type": "labubu4", "count": 5, "interval": 1.2},
     {"type": "labubu2", "count": 3, "interval": 1.5}],
    # Onda 6
    [{"type": "labubu1", "count": 8, "interval": 0.8},
     {"type": "labubu3", "count": 3, "interval": 2.0}],
    # Onda 7
    [{"type": "labubu3", "count": 5, "interval": 1.8},
     {"type": "labubu4", "count": 4, "interval": 1.4}],
    # Onda 8
    [{"type": "labubu2", "count": 8, "interval": 1.0},
     {"type": "labubu4", "count": 5, "interval": 1.2}],
    # Onda 9
    [{"type": "labubu4", "count": 8, "interval": 1.0},
     {"type": "labubu3", "count": 4, "interval": 1.8}],
    # Onda 10
    [{"type": "labubu3", "count": 6, "interval": 1.5},
     {"type": "labubu4", "count": 6, "interval": 1.2},
     {"type": "labubu2", "count": 4, "interval": 1.0}],
    # Onda 11
    [{"type": "labubu1", "count": 12, "interval": 0.6},
     {"type": "labubu4", "count": 6, "interval": 1.0}],
    # Onda 12
    [{"type": "labubu3", "count": 8, "interval": 1.2},
     {"type": "labubu4", "count": 8, "interval": 1.0}],
    # Onda 13
    [{"type": "labubu4", "count": 12, "interval": 0.8},
     {"type": "labubu3", "count": 6, "interval": 1.4}],
    # Onda 14 — última antes do boss
    [{"type": "labubu2", "count": 10, "interval": 0.8},
     {"type": "labubu3", "count": 8, "interval": 1.0},
     {"type": "labubu4", "count": 8, "interval": 0.9}],
    # Onda 15 — Boss Ancelotti (com escolta)
    [{"type": "labubu4", "count": 4, "interval": 1.5},
     {"type": "ancelotti", "count": 1, "interval": 2.0}],
]

# Segundos entre o fim de uma onda e o início da próxima.
WAVE_INTERVAL: float = 10.0

# Atraso até o início da primeira onda.
INITIAL_DELAY: float = 3.0


class WaveManager:
    """Gerencia o spawn dos inimigos onda a onda."""

    def __init__(self) -> None:
        self.current_wave: int = 0          # índice da onda atual em WAVES
        self.spawn_queue: list[dict] = []   # spawns individuais pendentes
        self.spawn_timer: float = 0.0       # tempo até o próximo spawn
        self.wave_timer: float = INITIAL_DELAY  # tempo até iniciar a próxima onda
        self.wave_active: bool = False

        # Modo de dificuldade (Bloco 5): setado no reset da partida. Aplica os
        # multiplicadores de MODOS_DIFICULDADE na criação de cada inimigo.
        self.modo: str = "normal"

        # Injetado pelo main após a criação (precisa do AssetManager).
        self.assets = None

        # Estado interno de controle.
        self._enemies_ref: list[Enemy] | None = None
        self._all_sent: bool = False

    # ------------------------------------------------------------------ #
    # Atualização
    # ------------------------------------------------------------------ #
    def update(self, dt: float, enemies: list[Enemy], waypoints: list[dict]) -> None:
        """Avança a temporização e spawna inimigos conforme a onda."""
        self._enemies_ref = enemies

        if self.wave_active:
            self._spawnar(dt, enemies, waypoints)
        elif self.current_wave < len(WAVES):
            # Aguardando o início da próxima onda.
            self.wave_timer -= dt
            if self.wave_timer <= 0.0:
                self._iniciar_onda()

    def _iniciar_onda(self) -> None:
        """Expande os grupos da onda atual em uma fila de spawns individuais."""
        self.spawn_queue = []
        for grupo in WAVES[self.current_wave]:
            for _ in range(grupo["count"]):
                self.spawn_queue.append(
                    {"type": grupo["type"], "interval": grupo["interval"]}
                )
        self.spawn_timer = 0.0  # primeiro inimigo sai imediatamente
        self.wave_active = True

    def _spawnar(self, dt: float, enemies: list[Enemy], waypoints: list[dict]) -> None:
        """Consome a fila de spawns no ritmo dos intervalos."""
        self.spawn_timer -= dt
        while self.spawn_queue and self.spawn_timer <= 0.0:
            spawn = self.spawn_queue.pop(0)
            classe = TIPOS[spawn["type"]]
            inimigo = classe(self.assets, waypoints)
            modo = MODOS_DIFICULDADE[self.modo]
            
            # Identifica o boss uma única vez para clareza
            is_boss = spawn["type"] == "ancelotti"

            # HP: escala por onda (+10%/onda, 1-based) só p/ não-boss.
            if not is_boss:
                wave_mult = 1.0 + (self.current_wave + 1) * 0.10
                base_hp = inimigo.max_hp * wave_mult
            else:
                base_hp = inimigo.max_hp
                
            inimigo.max_hp = round(base_hp * modo["hp_mult"])
            inimigo.hp = inimigo.max_hp
            
            # Velocidade de dificuldade
            inimigo.speed = inimigo.speed * modo["speed_mult"]
            
            # Labubu4 cacheia a velocidade base
            if hasattr(inimigo, "velocidade_base"):
                inimigo.velocidade_base *= modo["speed_mult"]
                
            # Economia: Recompensa escala por onda (+5%/onda) só para não-boss.
            if not is_boss:
                wave_reward_mult = 1.0 + (self.current_wave * 0.05)
                inimigo.reward = round(inimigo.reward * modo["reward_mult"] * wave_reward_mult)
            else:
                inimigo.reward = round(inimigo.reward * modo["reward_mult"])
                
            enemies.append(inimigo)
            self.spawn_timer += spawn["interval"]

        if not self.spawn_queue:
            # Onda enviada por completo: avança para a próxima.
            self.wave_active = False
            self.current_wave += 1
            if self.current_wave < len(WAVES):
                self.wave_timer = WAVE_INTERVAL
            else:
                self._all_sent = True

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def time_to_next_wave(self) -> float | None:
        """Segundos até a próxima onda (None se uma onda está em andamento)."""
        if not self.wave_active and self.current_wave < len(WAVES):
            return max(0.0, self.wave_timer)
        return None

    def forcar_fim_onda(self) -> None:
        """Encerra a wave ativa AGORA (usado pelo Skip durante a wave).

        Esvazia a fila de spawns pendentes e avança IMEDIATAMENTE para a próxima
        wave (v1.2.1: `wave_timer=0.0`, sem intervalo de espera — o Skip leva
        direto à onda seguinte). Os inimigos em campo são tratados pelo chamador
        (o Skip os elimina e concede o bônus).
        """
        if not self.wave_active:
            return
        self.spawn_queue.clear()
        self.wave_timer = 0.0      # avança imediato (Bloco 3)
        self.wave_active = False
        self.current_wave += 1
        if self.current_wave >= len(WAVES):
            self._all_sent = True

    def display_wave(self) -> int:
        """Número da onda para exibição (1-indexado, limitado ao total)."""
        return min(self.current_wave + 1, len(WAVES))

    def is_finished(self) -> bool:
        """True quando todas as ondas foram enviadas e não há mais inimigos."""
        return self._all_sent and not self._enemies_ref
