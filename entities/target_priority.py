"""Sistema de prioridade de alvo para torres.

Cada torre carrega seu próprio `priority: TargetPriority`. A função
`select_target()` encapsula toda a lógica de seleção — nenhuma torre
duplica essa lógica internamente.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TargetPriority(Enum):
    """Critérios de seleção de alvo. ONLY é reservado para uso futuro."""

    FIRST    = "primeiro"     # inimigo mais avançado no path — padrão
    LAST     = "ultimo"       # inimigo mais atrás no path
    STRONGEST = "mais_forte"  # maior HP atual
    WEAKEST  = "mais_fraco"   # menor HP atual
    ONLY     = "apenas"       # uso futuro (reservado)


def select_target(
    enemies: list,
    priority: TargetPriority,
    tower_range: float,
    tower_pos: tuple[float, float],
) -> object | None:
    """Retorna o inimigo alvo conforme prioridade, ou None se nenhum no alcance.

    Parâmetros:
        enemies: lista de Enemy (pode ser vazia — retorna None sem exceção)
        priority: critério de seleção
        tower_range: alcance em pixels
        tower_pos: (x, y) do centro da torre em pixels
    """
    if not enemies:
        return None

    cx, cy = tower_pos
    alcance2 = tower_range * tower_range

    no_alcance = [
        e for e in enemies
        if (e.x - cx) ** 2 + (e.y - cy) ** 2 <= alcance2
    ]
    if not no_alcance:
        return None

    if priority == TargetPriority.FIRST:
        return max(
            no_alcance,
            key=lambda e: (e.waypoint_index, -((e.x - cx) ** 2 + (e.y - cy) ** 2)),
        )

    if priority == TargetPriority.LAST:
        return min(
            no_alcance,
            key=lambda e: (e.waypoint_index, (e.x - cx) ** 2 + (e.y - cy) ** 2),
        )

    if priority == TargetPriority.STRONGEST:
        return max(no_alcance, key=lambda e: e.hp)

    if priority == TargetPriority.WEAKEST:
        return min(no_alcance, key=lambda e: e.hp)

    # ONLY: reservado — fallback para FIRST com aviso
    logger.warning(
        "Prioridade ONLY ainda não implementada — usando FIRST como fallback."
    )
    return select_target(enemies, TargetPriority.FIRST, tower_range, tower_pos)


def select_all_targets(enemies: list) -> list:
    """Retorna todos os inimigos no campo sem filtro de range.

    Usado por torres com full_aoe=True (KillThatBoy, KindaHomeless em campo
    inteiro, ShockedSpeed em modo buff). Lista vazia retorna lista vazia.
    """
    return list(enemies)
