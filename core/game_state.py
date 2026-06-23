"""Estado mutável compartilhado do jogo.

Container simples de dados (moedas, vidas, onda, torres, carta selecionada).
Não é uma máquina de estados — isso entra na Etapa 6.
"""

from dataclasses import dataclass, field

from config.settings import INITIAL_COINS, INITIAL_LIVES
from entities.enemy import Enemy
from entities.projectile import Projectile
from entities.tower import Tower
from entities.wave_manager import WaveManager


@dataclass
class GameState:
    """Dados de uma partida em andamento."""

    coins: int = INITIAL_COINS
    lives: int = INITIAL_LIVES
    wave: int = 1
    towers: list[Tower] = field(default_factory=list)
    enemies: list[Enemy] = field(default_factory=list)
    projectiles: list[Projectile] = field(default_factory=list)
    death_flashes: list[dict] = field(default_factory=list)
    wave_manager: WaveManager = field(default_factory=WaveManager)
    selected_card: int | None = None  # índice da carta selecionada
    selected_tower: Tower | None = None  # torre inspecionada (painel aberto)
    boss_defeated: bool = False
    kills: int = 0  # inimigos eliminados por dano
    map_grayscale: bool = False  # ativado pela habilidade do Speed7
    speed_multiplier: float = 1.0  # velocidade do jogo (1× ou 2×)
