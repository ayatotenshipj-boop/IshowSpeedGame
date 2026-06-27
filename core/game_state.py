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
    modo_dificuldade: str = "normal"  # facil | normal | dificil (Bloco 5)
    map_grayscale: bool = False  # ativado pela habilidade do Speed7
    speed_multiplier: float = 1.0  # velocidade do jogo (1× ou 2×)
    # Efeito temporário do Speed7: enquanto > 0, sprites em speed8 + mapa cinza
    # + suspense tocando. Ao zerar, tudo volta ao normal e a música retoma.
    speed7_effect_timer: float = 0.0
    # Cronômetro da partida (leaderboard). tempo_inicio = time.time() no 1º
    # spawn da onda 1; tempo_vitoria = duração total em segundos ao vencer.
    tempo_inicio: float = 0.0
    tempo_vitoria: float = 0.0
    # Skip Wave reformulado (v1.2.0): o skip aparece 15–20s após o início de uma
    # wave ATIVA (não no intervalo) e dá 1/4 das recompensas restantes.
    skip_timer: float = 0.0        # tempo desde o início da wave ativa
    skip_disponivel: bool = False  # True quando passou o limiar sorteado
    skip_threshold: float = 0.0    # limiar sorteado (15–20s); 0 = não armado
    auto_skip: bool = False        # toggle: aciona o skip sozinho ao ficar disponível
    auto_skip_timer: float = 3.0   # countdown do auto-skip quando disponível
    # VFX de AOE: anéis expansivos gerados por Speed4 (slow) e Speed5 buff.
    aoe_flashes: list = field(default_factory=list)
    # Waves congeladas enquanto o seletor de dificuldade estiver visível.
    waves_congeladas: bool = False
